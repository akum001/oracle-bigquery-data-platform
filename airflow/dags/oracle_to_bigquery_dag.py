from datetime import datetime, timedelta
from pathlib import Path

from airflow import DAG
from airflow.operators.python import PythonOperator

from src.extraction.oracle_extractor import OracleExtractor
from src.processing.transform_curated import CuratedProcessor
from src.warehouse.bigquery_loader import BigQueryWarehouseLoader

DEFAULT_CONFIG = Path("config/pipeline_config.yaml")

default_args = {
    "owner": "data-engineering",
    "depends_on_past": False,
    "email_on_failure": False,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=2),
}


def run_extract(**context) -> None:
    full_refresh = bool(context.get("params", {}).get("full_refresh", False))
    OracleExtractor(config_path=DEFAULT_CONFIG).run(full_refresh=full_refresh)


def run_transform(**context) -> None:
    CuratedProcessor(config_path=DEFAULT_CONFIG).run()


def run_load(**context) -> None:
    BigQueryWarehouseLoader(config_path=DEFAULT_CONFIG).run()


with DAG(
    dag_id="oracle_erp_to_bigquery_incremental",
    description="Incremental CDC extraction from Oracle 23ai Free to BigQuery analytics marts",
    default_args=default_args,
    start_date=datetime(2026, 11, 1),
    schedule="0 */6 * * *",
    catchup=False,
    max_active_runs=1,
    params={"full_refresh": False},
    tags=["oracle", "bigquery", "elt", "erp"],
) as dag:
    extract_oracle = PythonOperator(
        task_id="extract_oracle_incremental",
        python_callable=run_extract,
    )

    curate_silver = PythonOperator(
        task_id="curate_and_validate_silver",
        python_callable=run_transform,
    )

    load_bigquery = PythonOperator(
        task_id="merge_into_bigquery",
        python_callable=run_load,
    )

    extract_oracle >> curate_silver >> load_bigquery
