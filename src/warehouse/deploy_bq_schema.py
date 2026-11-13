import os
from pathlib import Path
from dotenv import load_dotenv
from google.cloud import bigquery


def main() -> None:
    load_dotenv(dotenv_path=Path(".env"))
    project_id = os.getenv("GCP_PROJECT_ID")
    location = os.getenv("BQ_LOCATION", "US")

    if not project_id:
        raise ValueError("GCP_PROJECT_ID is not set in .env")

    client = bigquery.Client(project=project_id, location=location)

    for sql_file in [
        "sql/bigquery/01_create_warehouse_tables.sql",
        "sql/bigquery/02_analytics_views.sql",
    ]:
        raw_sql = Path(sql_file).read_text(encoding="utf-8").replace("${PROJECT_ID}", project_id)
        statements = [s.strip() for s in raw_sql.split(";") if s.strip()]
        for stmt in statements:
            client.query(stmt).result()
        print(f"[OK] Deployed {len(statements)} statements from {sql_file} -> {project_id}")


if __name__ == "__main__":
    main()
