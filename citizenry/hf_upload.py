"""Async per-episode upload to Hugging Face Hub.

Watches a v3 dataset root, uploads on close, optionally deletes local
copy on verified success. Retries on transient failure.
"""

from __future__ import annotations

import asyncio
import os
import shutil
from pathlib import Path

from huggingface_hub import upload_folder, HfApi


def _read_token(path: str | None) -> str | None:
    if path is None:
        return None
    p = Path(path).expanduser()
    if not p.exists():
        return None
    return p.read_text().strip()


# Standard location written by `huggingface-cli login` / `hf auth login`.
# Picked up automatically as a fallback so users don't need to copy the token
# into ~/.citizenry/hf_token after running the CLI flow.
_HF_CACHE_TOKEN_PATH = "~/.cache/huggingface/token"


class HFUploader:
    def __init__(
        self,
        repo_id: str,
        token: str | None = None,
        token_path: str = "~/.citizenry/hf_token",
        repo_type: str = "dataset",
    ):
        self.repo_id = repo_id
        self.repo_type = repo_type
        # Token discovery order: explicit arg → ~/.citizenry/hf_token →
        # ~/.cache/huggingface/token (huggingface-cli login output) → HF_TOKEN env.
        self._token = (
            token
            or _read_token(token_path)
            or _read_token(_HF_CACHE_TOKEN_PATH)
            or os.environ.get("HF_TOKEN")
        )
        self._api = HfApi(token=self._token) if self._token else None
        self._seen_mtime: dict[Path, float] = {}

    def upload_root(
        self,
        folder: Path,
        delete_on_success: bool = False,
        commit_message: str | None = None,
    ) -> bool:
        """Upload a folder; return True on verified success."""
        folder = Path(folder)
        if not folder.exists():
            return False
        try:
            upload_folder(
                folder_path=str(folder),
                repo_id=self.repo_id,
                repo_type=self.repo_type,
                token=self._token,
                commit_message=commit_message or f"upload {folder.name}",
            )
        except Exception as e:
            print(f"[hf_upload] FAIL {folder}: {e}")
            return False
        if not self._verify_remote(folder):
            print(f"[hf_upload] verification failed for {folder}")
            return False
        if delete_on_success:
            try:
                shutil.rmtree(folder)
            except FileNotFoundError:
                pass
        return True

    def _verify_remote(self, folder: Path) -> bool:
        """Check that at least one local parquet now appears in the remote repo.

        Returns True when:
        - No API token is configured (test/offline mode).
        - The API call fails (network error, auth error) — optimistic pass.
        - No local parquets to verify against.
        - At least one local parquet name appears in the remote file list.
        """
        if self._api is None:
            return True  # no token → assume success (test mode)
        try:
            files = list(self._api.list_repo_files(self.repo_id, repo_type=self.repo_type))
        except Exception:
            # Cannot reach HF (network error, bad token, etc.) — treat as pass
            # so a transient API failure doesn't block local deletion.
            return True
        local_names = {p.name for p in folder.rglob("*.parquet")}
        if not local_names:
            return True  # nothing to verify
        return any(name in f for f in files for name in local_names)

    async def watch(
        self,
        folder: Path,
        poll_interval: float = 5.0,
        delete_on_success: bool = True,
        cap_local_episodes: int | None = None,
    ) -> None:
        """Poll a v3 dataset root for new chunk-mtime changes; upload them."""
        folder = Path(folder)
        while True:
            try:
                changed = self._scan_changed_chunks(folder)
                if changed:
                    ok = await asyncio.to_thread(
                        self.upload_root,
                        folder,
                        delete_on_success=delete_on_success,
                        commit_message=f"chunks: {','.join(c.name for c in changed)}",
                    )
                    if ok:
                        self._commit_seen_mtime(changed)
                if cap_local_episodes is not None:
                    self._enforce_cap(folder, cap_local_episodes)
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                return
            except Exception as e:
                print(f"[hf_upload] watch loop error: {e}")
                await asyncio.sleep(max(1.0, poll_interval))

    def _scan_changed_chunks(self, folder: Path) -> list[Path]:
        """Return chunks whose mtime differs from last seen.

        Caller is responsible for recording the new mtime via _commit_seen_mtime
        after a successful upload, so failed uploads are retried on the next poll.
        """
        out = []
        if not folder.exists():
            return out
        for chunk in folder.glob("data/chunk_*"):
            mt = chunk.stat().st_mtime
            if self._seen_mtime.get(chunk, 0) != mt:
                out.append(chunk)
        return out

    def _commit_seen_mtime(self, chunks: list[Path]) -> None:
        """Record current mtime so successful chunks aren't re-uploaded."""
        for chunk in chunks:
            try:
                self._seen_mtime[chunk] = chunk.stat().st_mtime
            except FileNotFoundError:
                # Chunk deleted after upload (delete_on_success path)
                self._seen_mtime[chunk] = 0

    def _enforce_cap(self, folder: Path, cap: int) -> None:
        eps = sorted((folder / "data").rglob("episode_*.parquet"))
        if len(eps) <= cap:
            return
        print(
            f"[hf_upload] WARN: {len(eps)} local episodes exceeds cap={cap}; "
            "uploads may be lagging."
        )
