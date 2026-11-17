import argparse
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

import oracledb
import pandas as pd
import yaml
from dotenv import load_dotenv

from src.common.storage import StorageIO, join_uri, resolve_data_path


class WatermarkStore:
    def __init__(self, state_file: str | Path) -> None:
        self.state_file = str(state_file)
        self.storage = StorageIO(self.state_file)
        self._state: Dict[str, str] = self._load()

    def _load(self) -> Dict[str, str]:
        return self.storage.read_json(self.state_file, default={})

    def get(self, table_name: str) -> Optional[datetime]:
        raw_val = self._state.get(table_name)
        if not raw_val:
            return None
        return datetime.fromisoformat(raw_val)

    def set(self, table_name: str, watermark_dt: datetime) -> None:
        self._state[table_name] = watermark_dt.isoformat()
        self.storage.write_json_atomic(self.state_file, self._state)


class OracleExtractor:
    def __init__(self, config_path: Path) -> None:
        load_dotenv()
        with config_path.open("r", encoding="utf-8") as f:
            self.cfg: Dict[str, Any] = yaml.safe_load(f)

        self.dsn = (
            f"{os.getenv('ORACLE_HOST')}:{os.getenv('ORACLE_PORT')}/"
            f"{os.getenv('ORACLE_SERVICE')}"
        )
        self.user = os.getenv("ORACLE_USER")
        self.password = os.getenv("ORACLE_APP_PWD")

        self.raw_dir = resolve_data_path(self.cfg["paths"]["raw_landing_dir"])
        self.raw_storage = StorageIO(self.raw_dir)
        state_dir = resolve_data_path(self.cfg["paths"]["state_dir"])
        self.watermarks = WatermarkStore(join_uri(state_dir, "watermarks.json"))
        self.source_system = self.cfg["source"]["system_name"]
        self.batch_size = int(self.cfg["source"].get("batch_size", 1000))

    def _connect(self) -> oracledb.Connection:
        return oracledb.connect(user=self.user, password=self.password, dsn=self.dsn)

    def extract_table(
        self,
        conn: oracledb.Connection,
        table_name: str,
        table_cfg: Dict[str, Any],
        full_refresh: bool = False,
    ) -> int:
        watermark_col = table_cfg["watermark_column"]
        mode = "full" if full_refresh else table_cfg.get("extract_mode", "incremental")
        last_wm = None if mode == "full" else self.watermarks.get(table_name)

        if last_wm is not None:
            sql = (
                f"SELECT * FROM {table_name} "
                f"WHERE {watermark_col} > :last_wm "
                f"ORDER BY {watermark_col} ASC"
            )
            params = {"last_wm": last_wm}
            effective_mode = "incremental"
        else:
            sql = f"SELECT * FROM {table_name} ORDER BY {watermark_col} ASC"
            params = {}
            effective_mode = "full"

        with conn.cursor() as cur:
            cur.arraysize = self.batch_size
            if "last_wm" in params:
                cur.setinputsizes(last_wm=oracledb.DB_TYPE_TIMESTAMP)
            cur.execute(sql, params)
            columns = [desc[0].lower() for desc in cur.description]
            rows = cur.fetchall()

        if not rows:
            print(
                f"  [SKIP] {table_name:<15} | mode={effective_mode:<11} | "
                f"0 new rows (watermark={last_wm.isoformat() if last_wm else 'None'})"
            )
            return 0

        df = pd.DataFrame(rows, columns=columns)
        run_ts = datetime.now(timezone.utc)
        df["_extracted_at_utc"] = run_ts.isoformat()
        df["_source_system"] = self.source_system
        df["_extract_mode"] = effective_mode

        partition_dir = join_uri(self.raw_dir, table_name, f"extract_date={run_ts.strftime('%Y-%m-%d')}")
        out_file = join_uri(partition_dir, f"{table_name}_{run_ts.strftime('%Y%m%dT%H%M%SZ')}.parquet")
        self.raw_storage.write_parquet(df, out_file)

        max_wm = pd.to_datetime(df[watermark_col]).max().to_pydatetime()
        self.watermarks.set(table_name, max_wm)

        print(
            f"  [OK]   {table_name:<15} | mode={effective_mode:<11} | "
            f"rows={len(df):<4} | new_watermark={max_wm.isoformat()} -> {out_file}"
        )
        return len(df)

    def run(self, full_refresh: bool = False) -> int:
        print(f"Starting Oracle extraction (full_refresh={full_refresh})...")
        total_rows = 0
        with self._connect() as conn:
            for table_name, table_cfg in self.cfg["tables"].items():
                total_rows += self.extract_table(
                    conn=conn,
                    table_name=table_name,
                    table_cfg=table_cfg,
                    full_refresh=full_refresh,
                )
        print(f"Extraction finished. Total rows extracted: {total_rows}")
        return total_rows


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract Oracle tables to raw Parquet.")
    parser.add_argument(
        "--config",
        type=Path,
        default=Path("config/pipeline_config.yaml"),
        help="Path to pipeline YAML config",
    )
    parser.add_argument(
        "--full-refresh",
        action="store_true",
        help="Ignore saved watermarks and extract full tables",
    )
    args = parser.parse_args()

    extractor = OracleExtractor(config_path=args.config)
    extractor.run(full_refresh=args.full_refresh)


if __name__ == "__main__":
    main()
