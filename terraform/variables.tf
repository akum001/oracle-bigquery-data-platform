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

variable "oracle_host" {
  description = "Private VPC or VPN IP/hostname for Oracle database"
  type        = string
  default     = "10.0.0.10"
}

variable "oracle_port" {
  description = "Oracle listener port"
  type        = string
  default     = "1521"
}

variable "oracle_service" {
  description = "Oracle pluggable database service name"
  type        = string
  default     = "FREEPDB1"
}

variable "oracle_user" {
  description = "Oracle application extraction user"
  type        = string
  default     = "SRC_ERP"
}

variable "schedule_cron" {
  description = "Cloud Scheduler cron schedule for incremental ELT runs"
  type        = string
  default     = "0 */6 * * *"
}
