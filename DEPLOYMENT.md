# AgriShield-X Deployment

This guide uses local AWS CLI credentials or environment variables. Do not paste secrets into files committed to Git.

## 1. Local Setup

```bash
python3 --version
node --version
aws --version
terraform version
```

Backend checks:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m pytest tests
python -c "from app.main import app; print(app.title)"
```

Frontend checks:

```bash
cd frontend
npm install
npm test -- --run
npm run build
```

Docker Compose check:

```bash
docker compose config
```

## 2. AWS CLI Setup

Configure AWS outside the repository:

```bash
aws configure
aws sts get-caller-identity
```

Expected region for this project is `ap-south-1`.

## 3. Terraform Apply

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
```

Edit `terraform.tfvars` locally:

```hcl
ssh_allowed_cidr = "YOUR_PUBLIC_IP/32"
key_name         = "your-existing-ec2-keypair"
bucket_name      = "globally-unique-s3-bucket-name"
```

Then run:

```bash
terraform init
terraform fmt
terraform validate
terraform plan
terraform apply
```

Useful outputs:

```bash
terraform output ec2_public_ip
terraform output backend_url
terraform output s3_bucket_name
terraform output s3_website_url
```

## 4. Backend Deployment

The backend deployment script clones the selected Git branch onto EC2 and starts PostgreSQL plus FastAPI through Docker Compose.

```bash
export EC2_HOST="$(terraform -chdir=infrastructure/terraform output -raw ec2_public_ip)"
export EC2_USER="ec2-user"
export SSH_KEY_PATH="/path/to/key.pem"
export REPO_URL="https://github.com/kingprem12/Agri-Shield.git"
export BRANCH="safe-terraform-deployment"
export POSTGRES_PASSWORD="replace-locally-only"
export CORS_ORIGINS='["*"]'
./scripts/deploy_backend_ec2.sh
```

Verify:

```bash
curl "http://${EC2_HOST}:8000/health"
curl "http://${EC2_HOST}:8000/benchmark"
```

## 5. Frontend Deployment

```bash
export S3_BUCKET="$(terraform -chdir=infrastructure/terraform output -raw s3_bucket_name)"
export VITE_API_BASE_URL="http://${EC2_HOST}:8000"
./scripts/deploy_frontend_s3.sh
```

Open the S3 website URL from Terraform output.

## 6. Destroy Infrastructure

```bash
./scripts/destroy_infra.sh
```

or:

```bash
cd infrastructure/terraform
terraform destroy
```

## Troubleshooting

- If SSH fails, confirm `ssh_allowed_cidr` matches your current public IP.
- If the backend does not start on a small EC2 instance, avoid building the frontend Docker image on that host.
- If S3 returns AccessDenied, confirm website hosting and bucket policy were applied.
- If CORS fails, set `CORS_ORIGINS` to the frontend website origin and redeploy the backend.
- If model files are missing, copy trained artifacts to `backend/models/` on the deployment host or mount a persistent model volume.

## Safety Checklist

Before every commit or push:

```bash
./scripts/check_secrets.sh
git status
git diff --cached --stat
```

Do not commit `.env`, PEM files, Terraform state, local datasets, virtual environments, `node_modules`, or large model artifacts.
