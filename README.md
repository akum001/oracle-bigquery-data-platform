# Oracle 23ai to BigQuery Incremental Data Platform

End-to-end ELT data engineering platform extracting transactional OLTP data from **Oracle Database 23ai Free** into partitioned **Bronze Parquet**, curating and validating **Silver datasets**, and upserting into partitioned/clustered **Google BigQuery** analytics marts via **Apache Airflow**.

## Architecture
1. **Source (`database/` & `docker/docker-compose.oracle.yml`):** Oracle 23ai Free (`FREEPDB1`) with `SRC_ERP` schema (`customers`, `products`, `orders`, `order_items`) and `updated_at` audit triggers.
2. **Extract (`src/extraction/oracle_extractor.py`):** Config-driven `oracledb` thin-mode incremental CDC extractor with atomic JSON watermark tracking (`data/state/watermarks.json`) writing date-partitioned Parquet files.
3. **Transform & DQ (`src/processing/transform_curated.py`):** Quarantine-enabled data quality gate, SCD Type 1 latest-state deduplication, standardization, and denormalized `fact_order_lines` mart enrichment.
4. **Warehouse (`src/warehouse/bigquery_loader.py` & `sql/bigquery/`):** Schema-contract validation and idempotent BigQuery `MERGE` loader (`dry_run` and `live` modes) targeting `DATE`-partitioned and clustered tables.
5. **Orchestration (`airflow/dags/oracle_to_bigquery_dag.py`):** Scheduled 6-hourly Airflow DAG + local CLI runner (`python -m src.run_pipeline`).

## Quickstart
    # 1. Start Oracle 23ai Free
    docker compose -f docker/docker-compose.oracle.yml --env-file .env up -d

    # 2. Run end-to-end pipeline
    source .venv/bin/activate
    python -m src.run_pipeline

    # 3. Run automated test suite
    pytest -v
