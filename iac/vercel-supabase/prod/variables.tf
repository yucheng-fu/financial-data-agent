variable "env" {
  type        = string
  description = "Environment name, e.g. test, prod. Becomes the app's ENVIRONMENT"
}

variable "supabase_organization_id" {
  type        = string
  description = "Supabase organization slug that owns the project"
}

variable "supabase_project_name" {
  type        = string
  description = "Supabase project name, unique within the organization"
}

variable "supabase_region" {
  type        = string
  description = "Supabase region, also the region of the S3 state backend"
}

variable "supabase_project_ref" {
  type        = string
  description = "Ref of the existing Supabase project to adopt, from its dashboard URL"

  validation {
    condition     = can(regex("^[a-z]{20}$", var.supabase_project_ref))
    error_message = "A Supabase project ref is 20 lowercase letters, as in supabase.com/dashboard/project/<ref>."
  }
}

variable "supabase_instance_size" {
  type        = string
  description = "Paid plan instance size. Null leaves the plan default, which the free tier requires"
  default     = null
}

variable "supabase_db_password" {
  type        = string
  description = "Password for the Supabase project database, supplied as TF_VAR_supabase_db_password"
  sensitive   = true
}

variable "llm_reader_db_password" {
  type        = string
  description = "Password for the llm_reader role, supplied as TF_VAR_llm_reader_db_password"
  sensitive   = true
}

variable "supabase_secret" {
  type        = string
  description = "Secret API key (sb_secret_...) the app uses for Storage, supplied as TF_VAR_supabase_secret"
  sensitive   = true
}

variable "vercel_project_name" {
  type        = string
  description = "Vercel project name, unique within the Vercel account"
}

variable "embedding_model" {
  type        = string
  description = "Embedding model the app loads, read as EMBEDDING_MODEL. Must produce 384 dimensions"
}

variable "llm_model" {
  type        = string
  description = "Gemini chat model, read as LLM_MODEL"
}

variable "google_api_key" {
  type        = string
  description = "Gemini API key, supplied as TF_VAR_google_api_key"
  sensitive   = true
}

variable "filings_bucket" {
  type        = string
  description = "Supabase Storage bucket holding the filings, created by hand. Read as FILINGS_BUCKET"
}
