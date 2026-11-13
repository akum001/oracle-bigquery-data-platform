resource "google_service_account" "pipeline_sa" {
  account_id   = "oracle-bq-pipeline"
  display_name = "Oracle 23ai to BigQuery ELT Pipeline Service Account"
  description  = "Least-privilege service account for staging and MERGE loading into BigQuery"
}

resource "google_project_iam_member" "bq_job_user" {
  project = var.project_id
  role    = "roles/bigquery.jobUser"
  member  = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_bigquery_dataset_iam_member" "dataset_editor" {
  dataset_id = google_bigquery_dataset.erp_analytics.dataset_id
  role       = "roles/bigquery.dataEditor"
  member     = "serviceAccount:${google_service_account.pipeline_sa.email}"
}
