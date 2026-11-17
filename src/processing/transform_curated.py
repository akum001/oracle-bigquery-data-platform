from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

import pandas as pd
import yaml

from src.common.storage import StorageIO, join_uri, resolve_data_path


class CuratedProcessor:
    def __init__(self, config_path: Path) -> None:
        with config_path.open("r", encoding="utf-8") as f:
            self.cfg: Dict[str, Any] = yaml.safe_load(f)

        self.raw_dir = resolve_data_path(self.cfg["paths"]["raw_landing_dir"])
        self.curated_dir = resolve_data_path(self.cfg["paths"]["curated_dir"])
        self.quarantine_dir = resolve_data_path(self.cfg["paths"]["quarantine_dir"])
        self.storage = StorageIO(self.raw_dir)

    def _load_raw_table(self, table_name: str) -> pd.DataFrame:
        files = self.storage.list_parquet_files(join_uri(self.raw_dir, table_name))
        if not files:
            raise FileNotFoundError(f"No raw parquet files found for table: {table_name}")
        frames = [self.storage.read_parquet(f) for f in files]
        return pd.concat(frames, ignore_index=True)

    def _deduplicate(self, df: pd.DataFrame, pk: str, watermark_col: str) -> pd.DataFrame:
        df = df.copy()
        df[watermark_col] = pd.to_datetime(df[watermark_col])
        df = df.sort_values(
            by=[watermark_col, "_extracted_at_utc"],
            ascending=[False, False],
        )
        return df.drop_duplicates(subset=[pk], keep="first").sort_values(by=pk).reset_index(drop=True)

    def _validate_and_split(
        self, table_name: str, df: pd.DataFrame, pk: str
    ) -> Tuple[pd.DataFrame, pd.DataFrame]:
        invalid_mask = df[pk].isna()

        if table_name == "customers":
            invalid_mask |= df["email"].isna() | ~df["email"].astype(str).str.contains("@")
        elif table_name == "products":
            invalid_mask |= (df["unit_price"] < 0) | (df["unit_cost"] < 0)
        elif table_name == "orders":
            invalid_mask |= df["customer_id"].isna() | df["order_status"].isna()
        elif table_name == "order_items":
            invalid_mask |= (df["quantity"] <= 0) | (df["unit_price"] < 0)

        valid_df = df[~invalid_mask].copy()
        quarantine_df = df[invalid_mask].copy()

        if not quarantine_df.empty:
            ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
            q_path = join_uri(self.quarantine_dir, f"{table_name}_quarantine_{ts}.parquet")
            self.storage.write_parquet(quarantine_df, q_path)

        return valid_df, quarantine_df

    def _standardize(self, table_name: str, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        for col in df.select_dtypes(include=["object", "string"]).columns:
            if not col.startswith("_"):
                df[col] = df[col].astype(str).str.strip()

        if table_name == "customers":
            df["email"] = df["email"].str.lower()
            df["country_code"] = df["country_code"].str.upper()
            df["segment"] = df["segment"].str.upper()
        elif table_name == "orders":
            df["order_status"] = df["order_status"].str.upper()
            df["currency_code"] = df["currency_code"].str.upper()
        elif table_name == "order_items":
            df["gross_amount"] = (df["quantity"] * df["unit_price"]).round(2)
            df["discount_amount"] = (df["gross_amount"] * (df["discount_pct"] / 100.0)).round(2)
            df["net_amount"] = (df["gross_amount"] - df["discount_amount"]).round(2)

        df["_curated_at_utc"] = datetime.now(timezone.utc).isoformat()
        return df

    def run(self) -> None:
        print("Running Bronze -> Silver curation & data quality checks...")
        curated_tables: Dict[str, pd.DataFrame] = {}

        for table_name, t_cfg in self.cfg["tables"].items():
            pk = t_cfg["primary_key"]
            wm = t_cfg["watermark_column"]

            raw_df = self._load_raw_table(table_name)
            valid_df, q_df = self._validate_and_split(table_name, raw_df, pk)
            dedup_df = self._deduplicate(valid_df, pk, wm)
            clean_df = self._standardize(table_name, dedup_df)

            curated_tables[table_name] = clean_df
            out_path = join_uri(self.curated_dir, f"{table_name}.parquet")
            self.storage.write_parquet(clean_df, out_path)

            print(
                f"  [OK] {table_name:<15} | raw_rows={len(raw_df):<3} | "
                f"quarantined={len(q_df):<2} | curated_rows={len(clean_df):<3} -> {out_path}"
            )

        items = curated_tables["order_items"]
        orders = curated_tables["orders"][
            ["order_id", "order_number", "customer_id", "order_status", "currency_code", "order_date"]
        ]
        customers = curated_tables["customers"][
            ["customer_id", "customer_code", "full_name", "segment", "country_code", "city"]
        ]
        products = curated_tables["products"][
            ["product_id", "sku", "product_name", "category", "unit_cost"]
        ]

        fact_lines = (
            items.merge(orders, on="order_id", how="inner")
            .merge(customers, on="customer_id", how="inner")
            .merge(products, on="product_id", how="inner")
        )
        fact_lines["line_cost"] = (fact_lines["quantity"] * fact_lines["unit_cost"]).round(2)
        fact_lines["gross_margin"] = (fact_lines["net_amount"] - fact_lines["line_cost"]).round(2)

        mart_path = join_uri(self.curated_dir, "fact_order_lines.parquet")
        self.storage.write_parquet(fact_lines, mart_path)
        print(f"  [OK] {'fact_order_lines':<15} | mart_rows={len(fact_lines):<3} -> {mart_path}")


if __name__ == "__main__":
    processor = CuratedProcessor(Path("config/pipeline_config.yaml"))
    processor.run()
