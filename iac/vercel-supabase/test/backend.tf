# State lives under terraform/ in this environment's filings bucket, in its own Supabase
# project, through Storage's S3-compatible API. The endpoint and keys come from
# AWS_ENDPOINT_URL_S3, AWS_ACCESS_KEY_ID and AWS_SECRET_ACCESS_KEY, set per GitHub
# environment, because a backend block cannot read variables.
#
# ponytail: no state lock. The workflow's per-environment concurrency group serializes
# runs; try use_lockfile = true if Supabase Storage supports conditional writes.
terraform {
  backend "s3" {
    bucket = "bucket-fda-test"
    key    = "terraform/test.tfstate"
    region = "eu-north-1"

    use_path_style              = true
    skip_credentials_validation = true
    skip_requesting_account_id  = true
    skip_metadata_api_check     = true
    skip_s3_checksum            = true
  }
}
