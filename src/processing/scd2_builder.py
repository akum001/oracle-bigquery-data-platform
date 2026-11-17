import hashlib
from datetime import datetime, timezone
from typing import List

import pandas as pd

from src.common.storage import StorageIO, resolve_data_path


def build_scd2_dimension(
    raw_df: pd.DataFrame,
    natural_key: str,
    tracked_cols: List[str],
    watermark_col: str = "updated_at",
) -> pd.DataFrame:
    df = raw_df.copy()
    df[watermark_col] = pd.to_datetime(df[watermark_col])

    df = df.sort_values(
        by=[natural_key, watermark_col, "_extracted_at_utc"],
        ascending=[True, True, True],
    ).reset_index(drop=True)

    attr_frame = df[tracked_cols].fillna("").astype(str)
    df["_attr_hash"] = attr_frame.apply(
        lambda row: hashlib.sha256("|".join(row).encode("utf-8")).hexdigest()[:16],
        axis=1,
    )

    prev_hash = df.groupby(natural_key)["_attr_hash"].shift(1)
    scd_df = df[df["_attr_hash"] != prev_hash].copy().reset_index(drop=True)

    scd_df["valid_from"] = scd_df[watermark_col]
    scd_df["valid_to"] = scd_df.groupby(natural_key)["valid_from"].shift(-1)
    scd_df["is_current"] = scd_df["valid_to"].isna()
    scd_df["valid_to"] = scd_df["valid_to"].fillna(pd.Timestamp("9999-12-31 23:59:59"))

    scd_df["surrogate_key"] = scd_df.apply(
        lambda r: hashlib.sha256(
            f"{r[natural_key]}|{r['valid_from'].isoformat()}".encode("utf-8")
        ).hexdigest()[:16],
        axis=1,
    )
    scd_df["_scd2_built_at_utc"] = datetime.now(timezone.utc).isoformat()

    return scd_df.drop(columns=["_attr_hash"])


def main() -> None:
    raw_customers_dir = resolve_data_path("data/raw/customers")
    storage = StorageIO(raw_customers_dir)
    raw_files = storage.list_parquet_files(raw_customers_dir)
    if not raw_files:
        raise FileNotFoundError("No raw customer parquet files found.")

    raw_customers = pd.concat([storage.read_parquet(f) for f in raw_files], ignore_index=True)
    for col in ["full_name", "city"]:
        raw_customers[col] = raw_customers[col].astype(str).str.strip()
    raw_customers["segment"] = raw_customers["segment"].astype(str).str.strip().str.upper()
    raw_customers["country_code"] = raw_customers["country_code"].astype(str).str.strip().str.upper()

    scd2_customers = build_scd2_dimension(
        raw_df=raw_customers,
        natural_key="customer_id",
        tracked_cols=["full_name", "segment", "country_code", "city", "is_active"],
    )

    out_path = resolve_data_path("data/curated/dim_customers_scd2.parquet")
    storage.write_parquet(scd2_customers, out_path)

    print(f"Built SCD2 dim_customers_scd2 -> {len(scd2_customers)} historical versions saved to {out_path}")
    cols = ["surrogate_key", "customer_id", "customer_code", "segment", "city", "valid_from", "valid_to", "is_current"]
    print(scd2_customers[cols].to_string(index=False))


if __name__ == "__main__":
    main()
