variable "project_name" {
  description = "Name prefix for AgriShield-X AWS resources."
  type        = string
  default     = "agrishield-x"
}

variable "aws_region" {
  description = "AWS region for deployment."
  type        = string
  default     = "ap-south-1"
}

variable "ssh_allowed_cidr" {
  description = "Public CIDR allowed to SSH into the EC2 instance, for example 203.0.113.10/32."
  type        = string
}

variable "key_name" {
  description = "Existing EC2 key pair name for SSH access."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for the backend."
  type        = string
  default     = "t3.micro"
}

variable "volume_size_gb" {
  description = "Root EBS volume size in GB."
  type        = number
  default     = 24
}

variable "bucket_name" {
  description = "Globally unique S3 bucket name for frontend static hosting. Leave null to generate one."
  type        = string
  default     = null
}

variable "environment" {
  description = "Deployment environment label."
  type        = string
  default     = "production"
}
