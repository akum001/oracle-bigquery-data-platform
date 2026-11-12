import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
import yaml
from dotenv import load_dotenv
from google.cloud import bigquery


EXPECTED_SCHEMAS: Dict[str, Dict[str, str]] = {
    "dim_customers": {
        "customer_id": "INT64",
        "customer_code": "STRING",
        "full_name": "STRING",
        "email": "STRING",
        "segment": "STRING",
        "country_code": "STRING",
        "city": "STRING",
        "is_active": "INT64",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    },
    "dim_products": {
        "product_id": "INT64",
        "sku": "STRING",
        "product_name": "STRING",
        "category": "STRING",
        "unit_price": "FLOAT64",
        "unit_cost": "FLOAT64",
        "is_active": "INT64",
        "created_at": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    },
    "fact_orders": {
        "order_id": "INT64",
        "order_number": "STRING",
        "customer_id": "INT64",
        "order_status": "STRING",
        "currency_code": "STRING",
        "order_date": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    },
    "fact_order_lines": {
        "order_item_id": "INT64",
        "order_id": "INT64",
        "order_number": "STRING",
        "customer_id": "INT64",
        "product_id": "INT64",
        "quantity": "INT64",
        "gross_amount": "FLOAT64",
        "discount_amount": "FLOAT64",
        "net_amount": "FLOAT64",
        "line_cost": "FLOAT64",
        "gross_margin": "FLOAT64",
        "order_date": "TIMESTAMP",
        "updated_at": "TIMESTAMP",
    },
}


class BigQueryWarehouseLoader:
    def __init__(self, config_path: Path) -> None:
        load_dotenv()
        with config_path.open("r", encoding="utf-8") as f:
            self.cfg: Dict[str, Any] = yaml.safe_load(f)

        self.project_id = os.getenv("GCP_PROJECT_ID", "local-oracle-bq-demo")
        self.dataset = os.getenv("BQ_DATASET", self.cfg["warehouse"]["dataset"])
        self.location = os.getenv("BQ_LOCATION", "US")
        self.load_mode = os.getenv("BQ_LOAD_MODE", "dry_run").lower()

        self.curated_dir = Path(self.cfg["paths"]["curated_dir"])
        self.state_dir = Path(self.cfg["paths"]["state_dir"])
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def _validate_contract(
        self, target_table: str, df: pd.DataFrame, pk: str, partition_field: str
    ) -> None:
        required_cols = EXPECTED_SCHEMAS[target_table]
        missing = [col for col in required_cols if col not in df.columns]
        if missing:
            raise ValueError(f"[{target_table}] Missing required BigQuery columns: {missing}")

        if df[pk].isna().any():
            raise ValueError(f"[{target_table}] Null primary keys detected in '{pk}'")

        if df[pk].duplicated().any():
            raise ValueError(f"[{target_table}] Duplicate primary keys detected in '{pk}'")

        if df[partition_field].isna().any():
            raise ValueError(
                f"[{target_table}] Null partition timestamps in '{partition_field}'"
            )

    def _build_merge_sql(self, target_table: str, pk: str, columns: List[str]) -> str:
        target_fqn = f"`{self.project_id}.{self.dataset}.{target_table}`"
        stage_fqn = f"`{self.project_id}.{self.dataset}._stg_{target_table}`"
        non_pk_cols = [c for c in columns if c != pk]

        update_clause = ",\n    ".join([f"T.{c} = S.{c}" for c in non_pk_cols])
        insert_cols = ", ".join(columns)
        insert_vals = ", ".join([f"S.{c}" for c in columns])

        return (
            f"MERGE {target_fqn} T\n"
            f"USING {stage_fqn} S\n"
            f"ON T.{pk} = S.{pk}\n"
            f"WHEN MATCHED THEN\n"
            f"  UPDATE SET\n    {update_clause}\n"
            f"WHEN NOT MATCHED THEN\n"
            f"  INSERT ({insert_cols})\n"
            f"  VALUES ({insert_vals});"
        )

    def _load_live(self, client: bigquery.Client, target_table: str, df: pd.DataFrame, pk: str) -> None:
        stage_table_id = f"{self.project_id}.{self.dataset}._stg_{target_table}"
        job_config = bigquery.LoadJobConfig(write_disposition="WRITE_TRUNCATE")
        load_job = client.load_table_from_dataframe(df, stage_table_id, job_config=job_config)
        load_job.result()

        merge_sql = self._build_merge_sql(target_table, pk, list(df.columns))
        client.query(merge_sql).result()
        client.delete_table(stage_table_id, not_found_ok=True)

    def run(self) -> None:
        print(
            f"Starting BigQuery warehouse load (project={self.project_id}, "
            f"dataset={self.dataset}, mode={self.load_mode})..."
        )
        client = bigquery.Client(project=self.project_id, location=self.location) if self.load_mode == "live" else None

        manifest: Dict[str, Any] = {
            "executed_at_utc": datetime.now(timezone.utc).isoformat(),
            "project_id": self.project_id,
            "dataset": self.dataset,
            "mode": self.load_mode,
            "tables": {},
        }

        for target_table, t_cfg in self.cfg["warehouse"]["tables"].items():
            parquet_path = self.curated_dir / t_cfg["source_file"]
            pk = t_cfg["primary_key"]
            partition_field = t_cfg["partition_field"]

            df = pd.read_parquet(parquet_path)
            self._validate_contract(target_table, df, pk, partition_field)
            merge_sql = self._build_merge_sql(target_table, pk, list(df.columns))

            if self.load_mode == "live" and client is not None:
                self._load_live(client, target_table, df, pk)
                status = "MERGED_LIVE"
            else:
                status = "VALIDATED_DRY_RUN"

            manifest["tables"][target_table] = {
                "status": status,
                "row_count": int(len(df)),
                "primary_key": pk,
                "partition_field": partition_field,
                "cluster_fields": t_cfg["cluster_fields"],
                "merge_sql_preview": merge_sql.splitlines()[0],
            }
            print(
                f"  [OK] {target_table:<18} | status={status:<18} | "
                f"rows={len(df):<3} | partition={partition_field} | cluster={t_cfg['cluster_fields']}"
            )

        manifest_path = self.state_dir / "bq_load_manifest.json"
        with manifest_path.open("w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)
        print(f"Warehouse load complete. Manifest saved -> {manifest_path}")


if __name__ == "__main__":
    loader = BigQueryWarehouseLoader(Path("config/pipeline_config.yaml"))
    loader.run()
