resource "google_storage_bucket" "data_lake" {
  name                        = "${var.project_id}-oracle-bq-datalake"
  location                    = var.region
  uniform_bucket_level_access = true
  force_destroy               = !var.deletion_protection

  versioning {
    enabled = true
  }

  lifecycle_rule {
    condition {
      age            = 90
      matches_prefix = ["quarantine/"]
    }
    action {
      type = "Delete"
    }
  }
}

resource "google_storage_bucket_iam_member" "pipeline_lake_admin" {
  bucket = google_storage_bucket.data_lake.name
  role   = "roles/storage.objectAdmin"
  member = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_artifact_registry_repository" "pipeline_repo" {
  location      = var.region
  repository_id = "oracle-bq-platform"
  description   = "Container images for Oracle 23ai to BigQuery ELT pipeline"
  format        = "DOCKER"
}

resource "google_secret_manager_secret" "oracle_password" {
  secret_id = "oracle-erp-app-pwd"

  replication {
    auto {}
  }
}

resource "google_secret_manager_secret_iam_member" "pipeline_secret_accessor" {
  secret_id = google_secret_manager_secret.oracle_password.secret_id
  role      = "roles/secretmanager.secretAccessor"
  member    = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_cloud_run_v2_job" "elt_pipeline" {
  name                = "oracle-to-bigquery-elt"
  location            = var.region
  deletion_protection = var.deletion_protection

  template {
    template {
      service_account = google_service_account.pipeline_sa.email
      timeout         = "900s"
      max_retries     = 1

      containers {
        image = "${var.region}-docker.pkg.dev/${var.project_id}/${google_artifact_registry_repository.pipeline_repo.repository_id}/elt-runner:latest"

        resources {
          limits = {
            cpu    = "1"
            memory = "1Gi"
          }
        }

        env {
          name  = "GCP_PROJECT_ID"
          value = var.project_id
        }
        env {
          name  = "BQ_DATASET"
          value = var.dataset_id
        }
        env {
          name  = "BQ_LOCATION"
          value = var.bq_location
        }
        env {
          name  = "BQ_LOAD_MODE"
          value = "live"
        }
        env {
          name  = "DATA_ROOT"
          value = "gs://${google_storage_bucket.data_lake.name}"
        }
        env {
          name  = "ORACLE_HOST"
          value = var.oracle_host
        }
        env {
          name  = "ORACLE_PORT"
          value = var.oracle_port
        }
        env {
          name  = "ORACLE_SERVICE"
          value = var.oracle_service
        }
        env {
          name  = "ORACLE_USER"
          value = var.oracle_user
        }
        env {
          name = "ORACLE_APP_PWD"
          value_source {
            secret_key_ref {
              secret  = google_secret_manager_secret.oracle_password.secret_id
              version = "latest"
            }
          }
        }
      }
    }
  }
}

resource "google_cloud_run_v2_job_iam_member" "scheduler_invoker" {
  location = google_cloud_run_v2_job.elt_pipeline.location
  name     = google_cloud_run_v2_job.elt_pipeline.name
  role     = "roles/run.invoker"
  member   = "serviceAccount:${google_service_account.pipeline_sa.email}"
}

resource "google_cloud_scheduler_job" "elt_schedule" {
  name        = "oracle-to-bigquery-elt-schedule"
  description = "Triggers incremental Oracle 23ai to BigQuery ELT Cloud Run Job"
  schedule    = var.schedule_cron
  time_zone   = "UTC"
  region      = var.region

  http_target {
    http_method = "POST"
    uri         = "https://${var.region}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${var.project_id}/jobs/${google_cloud_run_v2_job.elt_pipeline.name}:run"

    oauth_token {
      service_account_email = google_service_account.pipeline_sa.email
    }
  }
}
