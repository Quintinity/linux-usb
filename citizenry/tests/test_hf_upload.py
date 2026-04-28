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
    with patch("citizenry.hf_upload.upload_folder") as upload_mock:
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
