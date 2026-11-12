import argparse
from pathlib import Path

from src.extraction.oracle_extractor import OracleExtractor
from src.processing.transform_curated import CuratedProcessor
from src.warehouse.bigquery_loader import BigQueryWarehouseLoader


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full Oracle -> Curated -> BigQuery pipeline.")
    parser.add_argument("--config", type=Path, default=Path("config/pipeline_config.yaml"))
    parser.add_argument("--full-refresh", action="store_true")
    args = parser.parse_args()

    print("=== [1/3] EXTRACT: Oracle 23ai -> Raw Parquet ===")
    OracleExtractor(config_path=args.config).run(full_refresh=args.full_refresh)

    print("\n=== [2/3] TRANSFORM: Raw Parquet -> Silver Curated ===")
    CuratedProcessor(config_path=args.config).run()

    print("\n=== [3/3] LOAD: Silver Curated -> BigQuery Warehouse ===")
    BigQueryWarehouseLoader(config_path=args.config).run()
    print("\n=== PIPELINE SUCCEEDED ===")


if __name__ == "__main__":
    main()
