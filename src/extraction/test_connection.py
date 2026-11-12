import os
from pathlib import Path
import yaml
import oracledb
from dotenv import load_dotenv


def main() -> None:
    load_dotenv()

    config_path = Path("config/pipeline_config.yaml")
    with config_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    dsn = f"{os.getenv('ORACLE_HOST')}:{os.getenv('ORACLE_PORT')}/{os.getenv('ORACLE_SERVICE')}"
    user = os.getenv("ORACLE_USER")
    password = os.getenv("ORACLE_APP_PWD")

    print(f"Connecting to Oracle at {dsn} as {user} (thin mode={oracledb.is_thin_mode()})...")

    with oracledb.connect(user=user, password=password, dsn=dsn) as conn:
        with conn.cursor() as cur:
            for table_name in cfg["tables"].keys():
                cur.execute(f"SELECT COUNT(*) FROM {table_name}")
                (count,) = cur.fetchone()
                print(f"  [OK] {table_name:<15} -> {count} rows")


if __name__ == "__main__":
    main()
