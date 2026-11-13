output "dataset_id" {
  value = google_bigquery_dataset.erp_analytics.id
}

output "pipeline_service_account_email" {
  value = google_service_account.pipeline_sa.email
}

output "warehouse_table_ids" {
  value = [for t in google_bigquery_table.warehouse_tables : t.id]
}
