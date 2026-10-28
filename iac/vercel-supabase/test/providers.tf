terraform {
  # The s3 backend reads AWS_ENDPOINT_URL_S3 and use_path_style from 1.6 on.
  required_version = ">= 1.6"

  required_providers {
    supabase = {
      source  = "supabase/supabase"
      version = "1.11.0"
    }
    vercel = {
      source  = "vercel/vercel"
      version = "5.24.1"
    }
  }
}

# access_token comes from SUPABASE_ACCESS_TOKEN, set per GitHub environment.
provider "supabase" {}

# api_token comes from VERCEL_API_TOKEN, set per GitHub environment.
provider "vercel" {}
