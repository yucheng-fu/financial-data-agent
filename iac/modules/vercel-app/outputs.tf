output "project_id" {
  value       = vercel_project.this.id
  description = "Vercel project ID"
}

output "name" {
  value       = vercel_project.this.name
  description = "Vercel project name, which the pipeline links to before deploying"
}
