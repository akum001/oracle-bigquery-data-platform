variable "project_id" {
  description = "GCP Project ID hosting the BigQuery analytics warehouse"
  type        = string
}

variable "region" {
  description = "Default GCP compute/resource region"
  type        = string
  default     = "us-central1"
}

variable "bq_location" {
  description = "BigQuery dataset multi-region or regional location"
  type        = string
  default     = "US"
}

variable "dataset_id" {
  description = "BigQuery warehouse dataset name"
  type        = string
  default     = "erp_analytics"
}

variable "deletion_protection" {
  description = "Prevent accidental Terraform destruction of warehouse tables"
  type        = bool
  default     = false
}
