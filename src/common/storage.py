import io
import json
import os
from pathlib import Path
from typing import Any, Dict, List

import fsspec
import pandas as pd


def resolve_data_path(configured_path: str | Path) -> str:
    """Resolve a relative data path against DATA_ROOT (supports local paths and gs:// URIs)."""
    raw_str = str(configured_path).replace("\\", "/")
    data_root = os.getenv("DATA_ROOT", "").strip().rstrip("/")
    if not data_root:
        return raw_str

    rel = raw_str.removeprefix("data/").lstrip("/")
    return f"{data_root}/{rel}" if rel else data_root


def join_uri(base: str, *parts: str) -> str:
    cleaned = [base.rstrip("/")] + [str(p).strip("/") for p in parts if str(p).strip("/")]
    return "/".join(cleaned)


class StorageIO:
    """Unified filesystem helper supporting both local paths and gs:// URIs via fsspec/gcsfs."""

    def __init__(self, root_uri: str) -> None:
        self.root_uri = root_uri.rstrip("/")
        self.fs, self.fs_path = fsspec.core.url_to_fs(self.root_uri)
        self.is_gcs = self.root_uri.startswith("gs://")

    def _to_fs_path(self, uri: str) -> str:
        if uri.startswith("gs://"):
            _, path = fsspec.core.url_to_fs(uri)
            return path
        return uri

    def exists(self, uri: str) -> bool:
        return bool(self.fs.exists(self._to_fs_path(uri)))

    def ensure_parent(self, uri: str) -> None:
        if self.is_gcs:
            return
        Path(uri).parent.mkdir(parents=True, exist_ok=True)

    def read_json(self, uri: str, default: Any = None) -> Any:
        if not self.exists(uri):
            return {} if default is None else default
        with self.fs.open(self._to_fs_path(uri), "r", encoding="utf-8") as f:
            return json.load(f)

    def write_json_atomic(self, uri: str, payload: Any) -> None:
        self.ensure_parent(uri)
        serialized = json.dumps(payload, indent=2, sort_keys=True)
        if self.is_gcs:
            with self.fs.open(self._to_fs_path(uri), "w", encoding="utf-8") as f:
                f.write(serialized)
            return

        target = Path(uri)
        tmp_file = target.with_suffix(".tmp")
        with tmp_file.open("w", encoding="utf-8") as f:
            f.write(serialized)
        tmp_file.replace(target)

    def append_jsonl(self, uri: str, record: Dict[str, Any]) -> None:
        self.ensure_parent(uri)
        line = json.dumps(record) + "\n"
        if self.is_gcs:
            existing = ""
            if self.exists(uri):
                with self.fs.open(self._to_fs_path(uri), "r", encoding="utf-8") as f:
                    existing = f.read()
            with self.fs.open(self._to_fs_path(uri), "w", encoding="utf-8") as f:
                f.write(existing + line)
            return

        with Path(uri).open("a", encoding="utf-8") as f:
            f.write(line)

    def list_parquet_files(self, folder_uri: str) -> List[str]:
        fs_folder = self._to_fs_path(folder_uri)
        if not self.fs.exists(fs_folder):
            return []
        matches = sorted(self.fs.glob(f"{fs_folder}/**/*.parquet"))
        if self.is_gcs:
            return [m if m.startswith("gs://") else f"gs://{m}" for m in matches]
        return matches

    def read_parquet(self, uri: str) -> pd.DataFrame:
        with self.fs.open(self._to_fs_path(uri), "rb") as f:
            return pd.read_parquet(io.BytesIO(f.read()))

    def write_parquet(self, df: pd.DataFrame, uri: str) -> None:
        self.ensure_parent(uri)
        buf = io.BytesIO()
        df.to_parquet(buf, index=False, engine="pyarrow")
        with self.fs.open(self._to_fs_path(uri), "wb") as f:
            f.write(buf.getvalue())
