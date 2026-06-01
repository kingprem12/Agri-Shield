# AgriShield-X Terraform

This Terraform stack creates the AWS infrastructure needed for the AgriShield-X prototype:

- EC2 backend host
- Security group for SSH, HTTP, and FastAPI port `8000`
- S3 bucket configured for static website hosting

It does not store or require AWS secrets in files. Use your local AWS CLI profile or environment variables.

## Usage

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# Edit terraform.tfvars with your SSH CIDR, key pair name, and bucket name.
terraform init
terraform plan
terraform apply
```

Destroy resources:

```bash
terraform destroy
```

Do not commit `terraform.tfvars`, `.terraform/`, or Terraform state files.
