output "ec2_public_ip" {
  value = aws_instance.backend.public_ip
}

output "backend_url" {
  value = "http://${aws_instance.backend.public_ip}:8000"
}

output "frontend_url" {
  value = "http://${aws_s3_bucket_website_configuration.frontend.website_endpoint}"
}

output "s3_bucket_name" {
  value = aws_s3_bucket.frontend.bucket
}
