data "aws_caller_identity" "current" {}

data "aws_ami" "amazon_linux" {
  most_recent = true
  owners      = ["amazon"]

  filter {
    name   = "name"
    values = ["al2023-ami-*-x86_64"]
  }
}

locals {
  common_tags = {
    Project   = var.project_name
    ManagedBy = "terraform"
  }

  frontend_bucket = var.frontend_bucket_name != "" ? var.frontend_bucket_name : "${var.project_name}-frontend-${data.aws_caller_identity.current.account_id}-${var.aws_region}"
}
