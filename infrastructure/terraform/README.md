# AgriShield-X Terraform

This Terraform stack creates the reusable cloud foundation for AgriShield-X:

- EC2 backend host
- Security group with SSH from one operator CIDR, HTTP, and FastAPI port 8000
- IAM instance profile with AWS Systems Manager support
- S3 static website bucket for the React frontend

## Resources

- `aws_instance.backend`
- `aws_security_group.backend`
- `aws_iam_role.ec2_ssm`
- `aws_iam_instance_profile.ec2`
- `aws_s3_bucket.frontend`
- `aws_s3_bucket_website_configuration.frontend`
- `aws_s3_bucket_policy.frontend_public_read`

## Usage

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your own public IP/CIDR and optional bucket/key names
terraform init
terraform fmt -check
terraform validate
terraform plan
terraform apply
```

Destroy resources when finished:

```bash
terraform destroy
```

Do not commit `terraform.tfvars`, `.terraform/`, or Terraform state files.

## Outputs

- `ec2_public_ip`
- `backend_url`
- `frontend_url`
- `s3_bucket_name`

## Notes

The existing old EC2 deployment at `3.109.59.56` was created outside this Terraform stack and currently has no IAM instance profile. Use Terraform when a reproducible SSM-capable replacement is required.
