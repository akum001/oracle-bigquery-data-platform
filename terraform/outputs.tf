output "dataset_id" {
  value = google_bigquery_dataset.erp_analytics.id
}

output "pipeline_service_account_email" {
  value = google_service_account.pipeline_sa.email
}

output "warehouse_table_ids" {
  value = [for t in google_bigquery_table.warehouse_tables : t.id]
}

output "datalake_bucket_url" {
  description = "GCS bucket URI storing Bronze, Silver, Quarantine, and Watermark state"
  value       = "gs://${google_storage_bucket.data_lake.name}"
}

output "cloud_run_job_name" {
  description = "Serverless Cloud Run v2 Job executing the incremental ELT pipeline"
  value       = google_cloud_run_v2_job.elt_pipeline.name
}
