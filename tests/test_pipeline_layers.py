from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pytest
import yaml

from src.extraction.oracle_extractor import WatermarkStore
from src.processing.transform_curated import CuratedProcessor
from src.warehouse.bigquery_loader import BigQueryWarehouseLoader


@pytest.fixture()
def temp_workspace(tmp_path: Path) -> Path:
    raw_dir = tmp_path / "data" / "raw"
    curated_dir = tmp_path / "data" / "curated"
    quarantine_dir = tmp_path / "data" / "quarantine"
    state_dir = tmp_path / "data" / "state"

    for tbl in ["customers", "products", "orders", "order_items"]:
        (raw_dir / tbl / "extract_date=2026-11-12").mkdir(parents=True, exist_ok=True)

    run_ts = datetime.now(timezone.utc).isoformat()

    # Customers: includes duplicate customer_id=1 (older vs newer) + 1 bad email row for quarantine
    customers_df = pd.DataFrame(
        [
            {
                "customer_id": 1,
                "customer_code": "CUST-01",
                "full_name": "Old Name",
                "email": "user1@example.com",
                "segment": "retail",
                "country_code": "in",
                "city": "Delhi",
                "is_active": 1,
                "created_at": datetime(2026, 11, 1, 10, 0),
                "updated_at": datetime(2026, 11, 1, 10, 0),
                "_extracted_at_utc": run_ts,
            },
            {
                "customer_id": 1,
                "customer_code": "CUST-01",
                "full_name": "Updated Name",
                "email": "USER1@EXAMPLE.COM",
                "segment": "enterprise",
                "country_code": "in",
                "city": "Bengaluru",
                "is_active": 1,
                "created_at": datetime(2026, 11, 1, 10, 0),
                "updated_at": datetime(2026, 11, 5, 12, 0),
                "_extracted_at_utc": run_ts,
            },
            {
                "customer_id": 2,
                "customer_code": "CUST-BAD",
                "full_name": "Bad Email",
                "email": "invalid-email-no-at",
                "segment": "retail",
                "country_code": "us",
                "city": "NYC",
                "is_active": 1,
                "created_at": datetime(2026, 11, 1, 10, 0),
                "updated_at": datetime(2026, 11, 1, 10, 0),
                "_extracted_at_utc": run_ts,
            },
        ]
    )
    customers_df.to_parquet(
        raw_dir / "customers" / "extract_date=2026-11-12" / "part1.parquet", index=False
    )

    products_df = pd.DataFrame(
        [
            {
                "product_id": 10,
                "sku": "SKU-10",
                "product_name": "Sensor",
                "category": "IoT",
                "unit_price": 200.0,
                "unit_cost": 80.0,
                "is_active": 1,
                "created_at": datetime(2026, 11, 1, 9, 0),
                "updated_at": datetime(2026, 11, 1, 9, 0),
                "_extracted_at_utc": run_ts,
            }
        ]
    )
    products_df.to_parquet(
        raw_dir / "products" / "extract_date=2026-11-12" / "part1.parquet", index=False
    )

    orders_df = pd.DataFrame(
        [
            {
                "order_id": 100,
                "order_number": "ORD-100",
                "customer_id": 1,
                "order_status": "delivered",
                "currency_code": "usd",
                "order_date": datetime(2026, 11, 6, 14, 0),
                "updated_at": datetime(2026, 11, 6, 14, 0),
                "_extracted_at_utc": run_ts,
            }
        ]
    )
    orders_df.to_parquet(
        raw_dir / "orders" / "extract_date=2026-11-12" / "part1.parquet", index=False
    )

    items_df = pd.DataFrame(
        [
            {
                "order_item_id": 1000,
                "order_id": 100,
                "product_id": 10,
                "quantity": 3,
                "unit_price": 200.0,
                "discount_pct": 10.0,
                "updated_at": datetime(2026, 11, 6, 14, 0),
                "_extracted_at_utc": run_ts,
            }
        ]
    )
    items_df.to_parquet(
        raw_dir / "order_items" / "extract_date=2026-11-12" / "part1.parquet", index=False
    )

    cfg = {
        "source": {"system_name": "test_oracle", "schema": "SRC_ERP", "batch_size": 100},
        "tables": {
            "customers": {"primary_key": "customer_id", "watermark_column": "updated_at"},
            "products": {"primary_key": "product_id", "watermark_column": "updated_at"},
            "orders": {"primary_key": "order_id", "watermark_column": "updated_at"},
            "order_items": {"primary_key": "order_item_id", "watermark_column": "updated_at"},
        },
        "paths": {
            "raw_landing_dir": str(raw_dir),
            "state_dir": str(state_dir),
            "curated_dir": str(curated_dir),
            "quarantine_dir": str(quarantine_dir),
        },
        "warehouse": {
            "provider": "bigquery",
            "dataset": "erp_analytics",
            "tables": {
                "dim_customers": {
                    "source_file": "customers.parquet",
                    "primary_key": "customer_id",
                    "partition_field": "updated_at",
                    "cluster_fields": ["segment", "country_code"],
                },
                "dim_products": {
                    "source_file": "products.parquet",
                    "primary_key": "product_id",
                    "partition_field": "updated_at",
                    "cluster_fields": ["category", "sku"],
                },
                "fact_orders": {
                    "source_file": "orders.parquet",
                    "primary_key": "order_id",
                    "partition_field": "order_date",
                    "cluster_fields": ["order_status", "customer_id"],
                },
                "fact_order_lines": {
                    "source_file": "fact_order_lines.parquet",
                    "primary_key": "order_item_id",
                    "partition_field": "order_date",
                    "cluster_fields": ["category", "country_code"],
                },
            },
        },
    }

    cfg_path = tmp_path / "pipeline_config.yaml"
    with cfg_path.open("w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

    return cfg_path


def test_watermark_store_roundtrip(tmp_path: Path) -> None:
    store = WatermarkStore(tmp_path / "watermarks.json")
    assert store.get("orders") is None

    ts = datetime(2026, 11, 12, 17, 30, 0)
    store.set("orders", ts)

    reloaded = WatermarkStore(tmp_path / "watermarks.json")
    assert reloaded.get("orders") == ts


def test_curation_dedup_quarantine_and_warehouse_dry_run(
    temp_workspace: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BQ_LOAD_MODE", "dry_run")
    monkeypatch.setenv("GCP_PROJECT_ID", "unit-test-project")

    CuratedProcessor(temp_workspace).run()

    with temp_workspace.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    curated_dir = Path(cfg["paths"]["curated_dir"])
    quarantine_dir = Path(cfg["paths"]["quarantine_dir"])

    # Verify quarantine caught bad email row
    q_files = list(quarantine_dir.glob("customers_quarantine_*.parquet"))
    assert len(q_files) == 1
    assert len(pd.read_parquet(q_files[0])) == 1

    # Verify deduplication kept newer customer record & standardized casing
    cust = pd.read_parquet(curated_dir / "customers.parquet")
    assert len(cust) == 1
    assert cust.loc[0, "full_name"] == "Updated Name"
    assert cust.loc[0, "city"] == "Bengaluru"
    assert cust.loc[0, "email"] == "user1@example.com"
    assert cust.loc[0, "country_code"] == "IN"

    # Verify mart financial calculations: 3 * 200 = 600 gross, 10% = 60 disc, 540 net, 240 cost -> 300 margin
    mart = pd.read_parquet(curated_dir / "fact_order_lines.parquet")
    assert len(mart) == 1
    assert mart.loc[0, "gross_amount"] == 600.0
    assert mart.loc[0, "discount_amount"] == 60.0
    assert mart.loc[0, "net_amount"] == 540.0
    assert mart.loc[0, "gross_margin"] == 300.0

    # Verify BigQuery dry-run loader contract validation and manifest generation
    BigQueryWarehouseLoader(temp_workspace).run()
    manifest_file = Path(cfg["paths"]["state_dir"]) / "bq_load_manifest.json"
    assert manifest_file.exists()


def test_scd2_history_tracks_attribute_changes() -> None:
    from src.processing.scd2_builder import build_scd2_dimension

    df = pd.DataFrame(
        [
            {
                "customer_id": 2,
                "customer_code": "CUST-1002",
                "full_name": "Elena Rostova",
                "segment": "SMB",
                "country_code": "DE",
                "city": "Berlin",
                "is_active": 1,
                "updated_at": datetime(2026, 11, 2, 11, 30),
                "_extracted_at_utc": "2026-11-12T17:34:59+00:00",
            },
            # Exact duplicate extraction with no attribute change -> should NOT create a duplicate SCD2 row
            {
                "customer_id": 2,
                "customer_code": "CUST-1002",
                "full_name": "Elena Rostova",
                "segment": "SMB",
                "country_code": "DE",
                "city": "Berlin",
                "is_active": 1,
                "updated_at": datetime(2026, 11, 2, 11, 30),
                "_extracted_at_utc": "2026-11-12T17:35:10+00:00",
            },
            # Attribute update -> creates second historical version
            {
                "customer_id": 2,
                "customer_code": "CUST-1002",
                "full_name": "Elena Rostova",
                "segment": "ENTERPRISE",
                "country_code": "DE",
                "city": "Hyderabad",
                "is_active": 1,
                "updated_at": datetime(2026, 11, 12, 17, 35),
                "_extracted_at_utc": "2026-11-12T17:35:26+00:00",
            },
        ]
    )

    scd2 = build_scd2_dimension(
        raw_df=df,
        natural_key="customer_id",
        tracked_cols=["full_name", "segment", "country_code", "city", "is_active"],
    )
    assert len(scd2) == 2
    assert bool(scd2.loc[0, "is_current"]) is False
    assert scd2.loc[0, "city"] == "Berlin"
    assert scd2.loc[0, "valid_to"] == pd.Timestamp(datetime(2026, 11, 12, 17, 35))
    assert bool(scd2.loc[1, "is_current"]) is True
    assert scd2.loc[1, "city"] == "Hyderabad"
