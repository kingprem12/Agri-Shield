variable "aws_region" {
  description = "AWS region for AgriShield-X infrastructure."
  type        = string
  default     = "ap-south-1"
}

variable "project_name" {
  description = "Name prefix for AWS resources."
  type        = string
  default     = "agrishield-x"
}

variable "ssh_allowed_cidr" {
  description = "CIDR allowed to SSH into the backend EC2 instance."
  type        = string
}

variable "instance_type" {
  description = "EC2 instance type for the backend."
  type        = string
  default     = "t3.small"
}

variable "key_name" {
  description = "Optional EC2 key pair name. Leave empty when using SSM only."
  type        = string
  default     = ""
}

variable "frontend_bucket_name" {
  description = "Globally unique S3 bucket name for the frontend. Leave empty to derive one from account and region."
  type        = string
  default     = ""
}
