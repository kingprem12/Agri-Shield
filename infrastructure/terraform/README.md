# AgriShield-X Terraform

This Terraform stack creates the reusable cloud foundation for AgriShield-X:

- EC2 backend host
- Security group with SSH from one operator CIDR, HTTP, and FastAPI port 8000
- IAM instance profile with AWS Systems Manager support
- S3 static website bucket for the React frontend

## Usage

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# edit terraform.tfvars with your own public IP/CIDR and optional bucket/key names
terraform init
terraform plan
terraform apply
```

Destroy resources when finished:

```bash
terraform destroy
```

Do not commit `terraform.tfvars`, `.terraform/`, or Terraform state files.
