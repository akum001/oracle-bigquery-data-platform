-- BigQuery Warehouse DDL (Partitioned & Clustered for Cost-Optimized Analytics)
CREATE SCHEMA IF NOT EXISTS `${PROJECT_ID}.erp_analytics`
OPTIONS (location = 'US');

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.erp_analytics.dim_customers` (
  customer_id INT64 NOT NULL,
  customer_code STRING NOT NULL,
  full_name STRING NOT NULL,
  email STRING NOT NULL,
  segment STRING,
  country_code STRING,
  city STRING,
  is_active INT64,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  _curated_at_utc STRING
)
PARTITION BY DATE(updated_at)
CLUSTER BY segment, country_code;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.erp_analytics.dim_products` (
  product_id INT64 NOT NULL,
  sku STRING NOT NULL,
  product_name STRING NOT NULL,
  category STRING,
  unit_price FLOAT64,
  unit_cost FLOAT64,
  is_active INT64,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  _curated_at_utc STRING
)
PARTITION BY DATE(updated_at)
CLUSTER BY category, sku;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.erp_analytics.fact_orders` (
  order_id INT64 NOT NULL,
  order_number STRING NOT NULL,
  customer_id INT64 NOT NULL,
  order_status STRING,
  currency_code STRING,
  order_date TIMESTAMP,
  updated_at TIMESTAMP,
  _curated_at_utc STRING
)
PARTITION BY DATE(order_date)
CLUSTER BY order_status, customer_id;

CREATE TABLE IF NOT EXISTS `${PROJECT_ID}.erp_analytics.fact_order_lines` (
  order_item_id INT64 NOT NULL,
  order_id INT64 NOT NULL,
  order_number STRING NOT NULL,
  customer_id INT64 NOT NULL,
  customer_code STRING,
  full_name STRING,
  segment STRING,
  country_code STRING,
  city STRING,
  product_id INT64 NOT NULL,
  sku STRING,
  product_name STRING,
  category STRING,
  order_status STRING,
  currency_code STRING,
  order_date TIMESTAMP,
  quantity INT64,
  unit_price FLOAT64,
  discount_pct FLOAT64,
  gross_amount FLOAT64,
  discount_amount FLOAT64,
  net_amount FLOAT64,
  unit_cost FLOAT64,
  line_cost FLOAT64,
  gross_margin FLOAT64,
  updated_at TIMESTAMP,
  _curated_at_utc STRING
)
PARTITION BY DATE(order_date)
CLUSTER BY category, country_code;
