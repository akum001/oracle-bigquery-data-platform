locals {
  warehouse_tables = {
    dim_customers = {
      partition_field = "updated_at"
      clustering      = ["segment", "country_code"]
      description     = "SCD Type 1 Customer Dimension"
    }
    dim_products = {
      partition_field = "updated_at"
      clustering      = ["category", "sku"]
      description     = "SCD Type 1 Product Catalog Dimension"
    }
    fact_orders = {
      partition_field = "order_date"
      clustering      = ["order_status", "customer_id"]
      description     = "Order Header Fact Table"
    }
    fact_order_lines = {
      partition_field = "order_date"
      clustering      = ["category", "country_code"]
      description     = "Denormalized Order Line Analytics Mart"
    }
    dim_customers_scd2 = {
      partition_field = "valid_from"
      clustering      = ["customer_id", "is_current"]
      description     = "SCD Type 2 Historical Customer Dimension"
    }
  }
}

resource "google_bigquery_dataset" "erp_analytics" {
  dataset_id                 = var.dataset_id
  friendly_name              = "ERP Analytics Warehouse"
  description                = "Curated Silver/Gold warehouse loaded from Oracle 23ai Free"
  location                   = var.bq_location
  delete_contents_on_destroy = !var.deletion_protection
}

resource "google_bigquery_table" "warehouse_tables" {
  for_each = local.warehouse_tables

  dataset_id          = google_bigquery_dataset.erp_analytics.dataset_id
  table_id            = each.key
  description         = each.value.description
  deletion_protection = var.deletion_protection
  schema              = file("${path.module}/schemas/${each.key}.json")

  time_partitioning {
    type  = "DAY"
    field = each.value.partition_field
  }

  clustering = each.value.clustering
}

resource "google_bigquery_table" "vw_daily_revenue_kpis" {
  dataset_id          = google_bigquery_dataset.erp_analytics.dataset_id
  table_id            = "vw_daily_revenue_kpis"
  deletion_protection = false

  view {
    use_legacy_sql = false
    query          = <<-SQL
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
      FROM `${var.project_id}.${var.dataset_id}.fact_order_lines`
      WHERE order_status != 'CANCELLED'
      GROUP BY 1, 2
      ORDER BY 1 DESC
    SQL
  }

  depends_on = [google_bigquery_table.warehouse_tables]
}

resource "google_bigquery_table" "vw_category_segment_performance" {
  dataset_id          = google_bigquery_dataset.erp_analytics.dataset_id
  table_id            = "vw_category_segment_performance"
  deletion_protection = false

  view {
    use_legacy_sql = false
    query          = <<-SQL
      SELECT
        category,
        segment,
        country_code,
        COUNT(DISTINCT order_id) AS orders_count,
        SUM(quantity) AS units_sold,
        ROUND(SUM(net_amount), 2) AS net_revenue,
        ROUND(SUM(gross_margin), 2) AS gross_margin,
        ROUND(SAFE_DIVIDE(SUM(gross_margin), SUM(net_amount)) * 100, 2) AS margin_pct
      FROM `${var.project_id}.${var.dataset_id}.fact_order_lines`
      WHERE order_status != 'CANCELLED'
      GROUP BY 1, 2, 3
      ORDER BY net_revenue DESC
    SQL
  }

  depends_on = [google_bigquery_table.warehouse_tables]
}

resource "google_bigquery_table" "vw_customer_ltv" {
  dataset_id          = google_bigquery_dataset.erp_analytics.dataset_id
  table_id            = "vw_customer_ltv"
  deletion_protection = false

  view {
    use_legacy_sql = false
    query          = <<-SQL
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
      FROM `${var.project_id}.${var.dataset_id}.fact_order_lines`
      WHERE order_status != 'CANCELLED'
      GROUP BY 1, 2, 3, 4, 5, 6
      ORDER BY lifetime_net_revenue DESC
    SQL
  }

  depends_on = [google_bigquery_table.warehouse_tables]
}
