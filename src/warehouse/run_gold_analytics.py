from pathlib import Path
import duckdb


def main() -> None:
    mart_path = Path("data/curated/fact_order_lines.parquet")
    if not mart_path.exists():
        raise FileNotFoundError(f"Curated mart not found: {mart_path}. Run src.run_pipeline first.")

    con = duckdb.connect(database=":memory:")
    con.execute(f"CREATE VIEW fact_order_lines AS SELECT * FROM read_parquet('{mart_path}');")

    print("=== [GOLD KPI 1] Category & Customer Segment Performance ===")
    df_cat = con.execute("""
        SELECT
          category,
          segment,
          country_code,
          COUNT(DISTINCT order_id) AS orders,
          SUM(quantity) AS units,
          ROUND(SUM(net_amount), 2) AS net_revenue,
          ROUND(SUM(gross_margin), 2) AS gross_margin,
          ROUND(SUM(gross_margin) / NULLIF(SUM(net_amount), 0) * 100, 2) AS margin_pct
        FROM fact_order_lines
        WHERE order_status != 'CANCELLED'
        GROUP BY 1, 2, 3
        ORDER BY net_revenue DESC
    """).df()
    print(df_cat.to_string(index=False))

    print("\n=== [GOLD KPI 2] Customer Lifetime Value (LTV) Leaderboard ===")
    df_ltv = con.execute("""
        SELECT
          customer_code,
          full_name,
          segment,
          city,
          COUNT(DISTINCT order_id) AS orders,
          ROUND(SUM(net_amount), 2) AS ltv_net_revenue,
          ROUND(SUM(gross_margin), 2) AS ltv_margin
        FROM fact_order_lines
        WHERE order_status != 'CANCELLED'
        GROUP BY 1, 2, 3, 4
        ORDER BY ltv_net_revenue DESC
    """).df()
    print(df_ltv.to_string(index=False))


if __name__ == "__main__":
    main()
