"""Tests for HFUploader (mocked HF API)."""

import asyncio
import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from citizenry.hf_upload import HFUploader


@pytest.fixture
def fake_repo(tmp_path):
    root = tmp_path / "v3" / "test__local"
    (root / "data" / "chunk_0000").mkdir(parents=True)
    (root / "data" / "chunk_0000" / "episode_abc.parquet").write_bytes(b"dummy parquet")
    (root / "data" / "chunk_0000" / "episode_abc.json").write_text(json.dumps({"frame_count": 1}))
    return root


def test_upload_root_calls_hf_api(fake_repo, tmp_path):
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    with patch("citizenry.hf_upload.upload_folder") as upload_mock, \
         patch.object(uploader._api, "list_repo_files", return_value=["data/chunk_0000/episode_abc.parquet"]):
        upload_mock.return_value = MagicMock(commit_url="https://...")
        ok = uploader.upload_root(fake_repo)
    assert ok is True
    upload_mock.assert_called_once()
    call_kwargs = upload_mock.call_args.kwargs
    assert call_kwargs["repo_id"] == "user/repo"
    assert Path(call_kwargs["folder_path"]) == fake_repo


def test_upload_failure_returns_false_does_not_delete(fake_repo, tmp_path):
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    with patch("citizenry.hf_upload.upload_folder") as upload_mock:
        upload_mock.side_effect = RuntimeError("500 from HF")
        ok = uploader.upload_root(fake_repo, delete_on_success=True)
    assert ok is False
    # Files still present
    assert (fake_repo / "data" / "chunk_0000" / "episode_abc.parquet").exists()


def test_upload_success_with_delete_removes_local(fake_repo, tmp_path):
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    with patch("citizenry.hf_upload.upload_folder") as upload_mock, \
         patch.object(HFUploader, "_verify_remote", return_value=True):
        upload_mock.return_value = MagicMock(commit_url="https://...")
        ok = uploader.upload_root(fake_repo, delete_on_success=True)
    assert ok is True
    assert not (fake_repo / "data" / "chunk_0000" / "episode_abc.parquet").exists()


@pytest.mark.asyncio
async def test_watch_uploads_new_chunks(fake_repo, tmp_path):
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    uploaded = []

    def fake_upload_root(path, **kw):
        uploaded.append(Path(path).name)
        return True

    with patch.object(uploader, "upload_root", side_effect=fake_upload_root):
        task = asyncio.create_task(uploader.watch(fake_repo, poll_interval=0.05))
        await asyncio.sleep(0.15)
        # Drop a new chunk
        new_chunk = fake_repo / "data" / "chunk_0001"
        new_chunk.mkdir(parents=True)
        (new_chunk / "episode_xyz.parquet").write_bytes(b"new")
        await asyncio.sleep(0.20)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    # The watcher fires upload_root on parent dir each cycle; >=1 calls
    assert len(uploaded) >= 1


def test_scan_returns_chunk_again_after_failed_upload(tmp_path):
    """If upload fails, the next poll should still see the chunk as 'changed'
    until _commit_seen_mtime is called."""
    folder = tmp_path / "v3" / "test__local"
    chunk = folder / "data" / "chunk_0000"
    chunk.mkdir(parents=True)
    (chunk / "episode_abc.parquet").write_bytes(b"data")
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    # First scan finds the chunk
    first = uploader._scan_changed_chunks(folder)
    assert len(first) == 1
    # Without commit, second scan still finds it (retry semantics)
    second = uploader._scan_changed_chunks(folder)
    assert len(second) == 1
    # After commit, third scan finds nothing (assuming mtime unchanged)
    uploader._commit_seen_mtime(first)
    third = uploader._scan_changed_chunks(folder)
    assert len(third) == 0


def test_enforce_cap_logs_warning_when_over(tmp_path, capsys):
    folder = tmp_path / "v3" / "test__local"
    (folder / "data" / "chunk_0000").mkdir(parents=True)
    for i in range(5):
        (folder / "data" / "chunk_0000" / f"episode_{i:03d}.parquet").write_bytes(b"x")
    uploader = HFUploader(repo_id="user/repo", token="hf_dummy")
    uploader._enforce_cap(folder, cap=3)
    captured = capsys.readouterr()
    assert "exceeds cap" in captured.out
    # No warning when at or under cap
    uploader._enforce_cap(folder, cap=10)
    captured2 = capsys.readouterr()
    assert "exceeds cap" not in captured2.out


def test_uploader_falls_back_to_hf_cache_token(tmp_path, monkeypatch):
    """When ~/.citizenry/hf_token is missing, fall back to ~/.cache/huggingface/token
    (the location populated by `huggingface-cli login`)."""
    citizenry_token = tmp_path / "citizenry_hf_token"  # doesn't exist
    hf_cache_token = tmp_path / "hf_cache_token"
    hf_cache_token.write_text("hf_cli_token_value\n")  # CLI writes a trailing newline
    monkeypatch.setattr("citizenry.hf_upload._HF_CACHE_TOKEN_PATH", str(hf_cache_token))
    monkeypatch.delenv("HF_TOKEN", raising=False)
    uploader = HFUploader(repo_id="user/repo", token=None, token_path=str(citizenry_token))
    assert uploader._token == "hf_cli_token_value"


def test_uploader_explicit_token_wins_over_files(tmp_path, monkeypatch):
    """Explicit token arg trumps both ~/.citizenry/hf_token and the HF cache."""
    citizenry_token = tmp_path / "ct"
    citizenry_token.write_text("citizenry_value")
    hf_cache_token = tmp_path / "hf"
    hf_cache_token.write_text("hf_cache_value")
    monkeypatch.setattr("citizenry.hf_upload._HF_CACHE_TOKEN_PATH", str(hf_cache_token))
    monkeypatch.setenv("HF_TOKEN", "env_value")
    uploader = HFUploader(repo_id="user/repo", token="explicit", token_path=str(citizenry_token))
    assert uploader._token == "explicit"


def test_uploader_citizenry_token_wins_over_cache(tmp_path, monkeypatch):
    """~/.citizenry/hf_token takes precedence over the HF cache."""
    citizenry_token = tmp_path / "ct"
    citizenry_token.write_text("citizenry_value")
    hf_cache_token = tmp_path / "hf"
    hf_cache_token.write_text("hf_cache_value")
    monkeypatch.setattr("citizenry.hf_upload._HF_CACHE_TOKEN_PATH", str(hf_cache_token))
    monkeypatch.delenv("HF_TOKEN", raising=False)
    uploader = HFUploader(repo_id="user/repo", token=None, token_path=str(citizenry_token))
    assert uploader._token == "citizenry_value"
