output "ec2_public_ip" {
  description = "Public IPv4 address of the backend EC2 instance."
  value       = aws_instance.backend.public_ip
}

output "backend_url" {
  description = "FastAPI backend URL."
  value       = "http://${aws_instance.backend.public_ip}:8000"
}

output "s3_bucket_name" {
  description = "Frontend S3 bucket name."
  value       = aws_s3_bucket.frontend.bucket
}

output "s3_website_url" {
  description = "S3 static website endpoint."
  value       = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}
