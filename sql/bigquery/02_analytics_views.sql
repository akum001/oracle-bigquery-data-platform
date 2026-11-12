-- BigQuery Gold Layer Views (Business KPIs & Executive Marts)

CREATE OR REPLACE VIEW `${PROJECT_ID}.erp_analytics.vw_daily_revenue_kpis` AS
SELECT
  DATE(order_date) AS order_day,
  currency_code,
  COUNT(DISTINCT order_id) AS total_orders,
  SUM(quantity) AS total_units_sold,
  ROUND(SUM(gross_amount), 2) AS gross_revenue,
  ROUND(SUM(discount_amount), 2) AS total_discounts,
  ROUND(SUM(net_amount), 2) AS net_revenue,
  ROUND(SUM(gross_margin), 2) AS total_gross_margin,
  ROUND(SAFE_DIVIDE(SUM(gross_margin), SUM(net_amount)) * 100, 2) AS margin_pct
FROM `${PROJECT_ID}.erp_analytics.fact_order_lines`
WHERE order_status != 'CANCELLED'
GROUP BY 1, 2
ORDER BY 1 DESC;

CREATE OR REPLACE VIEW `${PROJECT_ID}.erp_analytics.vw_category_segment_performance` AS
SELECT
  category,
  segment,
  country_code,
  COUNT(DISTINCT order_id) AS orders_count,
  SUM(quantity) AS units_sold,
  ROUND(SUM(net_amount), 2) AS net_revenue,
  ROUND(SUM(gross_margin), 2) AS gross_margin,
  ROUND(SAFE_DIVIDE(SUM(gross_margin), SUM(net_amount)) * 100, 2) AS margin_pct
FROM `${PROJECT_ID}.erp_analytics.fact_order_lines`
WHERE order_status != 'CANCELLED'
GROUP BY 1, 2, 3
ORDER BY net_revenue DESC;

CREATE OR REPLACE VIEW `${PROJECT_ID}.erp_analytics.vw_customer_ltv` AS
SELECT
  customer_id,
  customer_code,
  full_name,
  segment,
  country_code,
  city,
  COUNT(DISTINCT order_id) AS lifetime_orders,
  SUM(quantity) AS lifetime_units,
  ROUND(SUM(net_amount), 2) AS lifetime_net_revenue,
  ROUND(SUM(gross_margin), 2) AS lifetime_gross_margin,
  MIN(order_date) AS first_order_at,
  MAX(order_date) AS last_order_at
FROM `${PROJECT_ID}.erp_analytics.fact_order_lines`
WHERE order_status != 'CANCELLED'
GROUP BY 1, 2, 3, 4, 5, 6
ORDER BY lifetime_net_revenue DESC;
