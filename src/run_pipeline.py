import argparse
import time
from pathlib import Path

from src.extraction.oracle_extractor import OracleExtractor
from src.observability.audit_logger import PipelineAuditLogger
from src.processing.scd2_builder import main as build_scd2
from src.processing.transform_curated import CuratedProcessor
from src.warehouse.bigquery_loader import BigQueryWarehouseLoader


def main() -> None:
    parser = argparse.ArgumentParser(description="Run full Oracle -> Curated -> BigQuery pipeline.")
    parser.add_argument("--config", type=Path, default=Path("config/pipeline_config.yaml"))
    parser.add_argument("--full-refresh", action="store_true")
    args = parser.parse_args()

    audit = PipelineAuditLogger()
    print(f"=== PIPELINE RUN START (run_id={audit.run_id}) ===")

    try:
        t0 = time.perf_counter()
        print("\n=== [1/4] EXTRACT: Oracle 23ai -> Raw Parquet ===")
        OracleExtractor(config_path=args.config).run(full_refresh=args.full_refresh)
        audit.record_stage("extract", time.perf_counter() - t0, "SUCCESS", {"full_refresh": args.full_refresh})

        t0 = time.perf_counter()
        print("\n=== [2/4] TRANSFORM: Raw Parquet -> Silver Curated ===")
        CuratedProcessor(config_path=args.config).run()
        audit.record_stage("transform_silver", time.perf_counter() - t0, "SUCCESS")

        t0 = time.perf_counter()
        print("\n=== [3/4] HISTORY: Build SCD Type 2 Customer Dimension ===")
        build_scd2()
        audit.record_stage("build_scd2", time.perf_counter() - t0, "SUCCESS")

        t0 = time.perf_counter()
        print("\n=== [4/4] LOAD: Silver Curated -> BigQuery Warehouse ===")
        BigQueryWarehouseLoader(config_path=args.config).run()
        audit.record_stage("load_bigquery", time.perf_counter() - t0, "SUCCESS")

        summary = audit.finalize("SUCCEEDED")
        print(f"\n=== PIPELINE SUCCEEDED (run_id={summary['run_id']}, duration={summary['total_duration_sec']}s) ===")
    except Exception as exc:
        audit.finalize("FAILED", error_message=str(exc))
        raise


if __name__ == "__main__":
    main()
