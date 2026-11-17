from pathlib import Path

import pandas as pd

from src.common.storage import StorageIO, join_uri, resolve_data_path


def test_resolve_data_path_local_default(monkeypatch) -> None:
    monkeypatch.delenv("DATA_ROOT", raising=False)
    assert resolve_data_path("data/raw") == "data/raw"
    assert resolve_data_path("data/state/watermarks.json") == "data/state/watermarks.json"


def test_resolve_data_path_gcs_override(monkeypatch) -> None:
    monkeypatch.setenv("DATA_ROOT", "gs://demo-lake-bucket/")
    assert resolve_data_path("data/raw") == "gs://demo-lake-bucket/raw"
    assert resolve_data_path("data/curated/fact_order_lines.parquet") == "gs://demo-lake-bucket/curated/fact_order_lines.parquet"
    assert join_uri("gs://demo-lake-bucket/raw", "customers", "extract_date=2026-11-16") == (
        "gs://demo-lake-bucket/raw/customers/extract_date=2026-11-16"
    )


def test_storage_io_roundtrip_local(tmp_path: Path) -> None:
    base = str(tmp_path)
    storage = StorageIO(base)

    json_uri = join_uri(base, "state", "watermarks.json")
    storage.write_json_atomic(json_uri, {"orders": "2026-11-16T10:00:00"})
    assert storage.read_json(json_uri) == {"orders": "2026-11-16T10:00:00"}

    pq_uri = join_uri(base, "raw", "orders", "extract_date=2026-11-16", "orders.parquet")
    df = pd.DataFrame([{"order_id": 1, "amount": 99.5}])
    storage.write_parquet(df, pq_uri)

    files = storage.list_parquet_files(join_uri(base, "raw", "orders"))
    assert len(files) == 1
    loaded = storage.read_parquet(files[0])
    assert loaded.to_dict(orient="records") == [{"order_id": 1, "amount": 99.5}]
