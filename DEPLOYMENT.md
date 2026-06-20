# AgriShield-X Deployment

## Local Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

```bash
cd frontend
npm install
VITE_API_BASE_URL=http://localhost:8000 npm run dev
```

## Secure Environment

Create a local `.env` from `.env.example` and replace placeholders. Do not commit `.env`.

Required production values:

- `DATABASE_URL`
- `JWT_SECRET_KEY`
- `SEED_ADMIN_EMAIL`
- `SEED_ADMIN_PASSWORD`
- `MODEL_PATH`

## Terraform

```bash
cd infrastructure/terraform
cp terraform.tfvars.example terraform.tfvars
# set ssh_allowed_cidr to your public IP/32
terraform init
terraform plan
terraform apply
```

Outputs include the EC2 public IP, backend URL, S3 frontend URL, and bucket name.

Destroy resources:

```bash
terraform destroy
```

## Backend Deployment

Use the existing deployment script or SSH/SSM into the EC2 instance. Preserve environment variables and database volume.

```bash
scripts/deploy_backend_ec2.sh
```

Verify:

```bash
curl http://EC2_PUBLIC_IP:8000/health
curl http://EC2_PUBLIC_IP:8000/pso-future/metrics
```

## Frontend Deployment

```bash
cd frontend
VITE_API_BASE_URL=http://EC2_PUBLIC_IP:8000 npm run build
aws s3 sync dist/ s3://YOUR_BUCKET --delete
```

## Troubleshooting

- A `401` response means the route requires login.
- A `403` response on `/admin/*` means the user is not an ADMIN.
- If the frontend shows stale routes, clear browser storage and reload.
- If SSM is unavailable, confirm the EC2 instance profile has `AmazonSSMManagedInstanceCore`.
