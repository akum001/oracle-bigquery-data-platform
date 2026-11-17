# Oracle 23ai to Google BigQuery Incremental ELT Data Platform

An end-to-end, config-driven modern data engineering platform that extracts incremental changes from **Oracle Database 23ai Free** into a partitioned **Bronze** Parquet landing zone, enforces data quality quarantine gates and **SCD Type 1 / Type 2** modeling in **Silver**, and executes idempotent, schema-aligned **`MERGE`** upserts into partitioned and clustered **Google BigQuery** analytics marts.

---

## Architecture Overview

```text
+-------------------+      Incremental CDC (DB_TYPE_TIMESTAMP)      +------------------------------------+
| Oracle 23ai Free  | --------------------------------------------> | Bronze Landing (Parquet)           |
| (Docker / PDB1)   |      Atomic JSON Watermark Store              | data/raw/<table>/extract_date=...  |
+-------------------+                                               +------------------------------------+
                                                                                      |
                                                                                      v
+-------------------+      Idempotent BigQuery MERGE (UTC)          +------------------------------------+
| Google BigQuery   | <-------------------------------------------- | Silver Curated & SCD Type 2        |
| (erp_analytics)   |      Partitioned & Clustered Warehouse        | Quarantine DQ + History Versioning |
+-------------------+                                               +------------------------------------+
        |
        v
+--------------------------------------------------------------------------------------------------------+
| Gold Analytics Views: vw_daily_revenue_kpis | vw_category_segment_performance | vw_customer_ltv         |
+--------------------------------------------------------------------------------------------------------+

oracle-bigquery-data-platform/
├── airflow/dags/                # Airflow DAG with ShortCircuitOperator for idle runs
├── config/pipeline_config.yaml  # Declarative table, watermark, partition, & cluster config
├── docker/oracle/               # Oracle 23ai Free Docker Compose & SRC_ERP DDL/seed SQL
├── sql/bigquery/                # Warehouse table DDL & Gold KPI analytics views
├── src/
│   ├── extraction/              # Thin-mode Oracle extractor & atomic WatermarkStore
│   ├── observability/           # Structured JSONL stage-level audit logger
│   ├── processing/              # Bronze -> Silver DQ curation & SCD Type 2 builder
│   ├── warehouse/               # BigQuery DDL deployer & idempotent MERGE loader
│   └── run_pipeline.py          # End-to-end CLI orchestrator (--full-refresh, --force-load)
├── terraform/                   # GCP BigQuery dataset, tables, views, & IAM service account
├── tests/                       # Pytest unit & integration suite
└── .github/workflows/ci.yml     # Automated pytest + Terraform fmt/validate CI pipeline

docker compose -f docker/oracle/docker-compose.yml up -d
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# Set ORACLE_HOST, ORACLE_PORT, ORACLE_SERVICE, ORACLE_USER, ORACLE_APP_PWD
# Set GCP_PROJECT_ID, BQ_LOCATION, BQ_LOAD_MODE (dry_run | live), GOOGLE_APPLICATION_CREDENTIALS
python -m src.warehouse.deploy_bq_schema
python -m src.run_pipeline              # Incremental run (short-circuits if 0 new rows)
python -m src.run_pipeline --force-load # Force Silver + SCD2 + BigQuery MERGE
python -m src.run_pipeline --full-refresh
pytest -v
terraform -chdir=terraform fmt -check -recursive
terraform -chdir=terraform validate
---

### Step 2: Push to GitHub & Trigger Live CI
If you have `gh` (GitHub CLI) installed or a new empty repository created on GitHub:

* **Option A (Using GitHub CLI `gh` if installed):**
  ```bash
  gh repo create oracle-bigquery-data-platform --public --source=. --remote=origin --push
