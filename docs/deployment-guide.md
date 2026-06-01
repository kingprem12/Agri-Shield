# Deployment Guide

## Local Validation

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements-research.txt
python scripts/run_etl.py --sample
python scripts/train_model.py
python scripts/train_deep_hybrid_benchmark.py --dataset-dir "/Users/prem/Documents/My Final year Project/Data Sets" --limit-files 276 --max-grid-rows 10000 --epochs 8
python scripts/generate_deep_hybrid_plots.py
pytest

cd ../frontend
npm install
npm test
npm run build
```

The deep-hybrid benchmark writes:

- `backend/reports/deep_hybrid_benchmark.json`
- `backend/models/deep_hybrid/`
- `backend/reports/plots/deep_hybrid/`

The report intentionally separates strict future forecasting, paper-comparable random split, same-month estimation, and spatial holdout. Only same-month estimation should be described as paper-comparable estimation, not future forecasting.

## Docker Compose

```bash
docker compose up --build
```

## AWS Backend on EC2

1. Launch Ubuntu EC2.
2. Open ports `22`, `80`, `443`, and optionally `8000` for temporary testing.
3. Run `infrastructure/aws/ec2-user-data.sh` as user data or manually.
4. Clone this repository into `/opt/agrishield-ai`.
5. Run:

```bash
./scripts/deploy_backend_ec2.sh ubuntu@YOUR_EC2_HOST git@github.com:YOUR_USER/agrishield-ai.git
```

Set production environment variables for PostgreSQL and model/report paths before starting the backend container. Keep large trained model artifacts either on the EC2 attached volume or in S3 and copy them into `backend/models/` during deployment.

## Render Backend Alternative

1. Create a new Render Web Service from the repository.
2. Use Docker deployment from `backend/Dockerfile`.
3. Add a managed PostgreSQL instance and set the database URL environment variable used by the backend settings.
4. Upload or restore `backend/models/` and `backend/reports/` as persistent disk content.
5. Expose the service URL as `VITE_API_BASE_URL` for the frontend.

## Nginx and HTTPS

Point your DNS record to EC2, then run:

```bash
./scripts/setup_https_nginx.sh api.your-domain.com you@example.com
```

## AWS Frontend on S3

1. Create an S3 bucket with static website hosting.
2. Configure CloudFront if HTTPS/custom domain is required.
3. Run:

```bash
./scripts/deploy_frontend_s3.sh your-s3-bucket
```

## Vercel Frontend Alternative

1. Import `frontend/` as the Vercel project root.
2. Set `VITE_API_BASE_URL` to the deployed backend URL.
3. Build command: `npm run build`.
4. Output directory: `dist`.

## Deployment Status

Cloud deployment requires the target AWS/Render/Vercel credentials and project identifiers. Do not mark the project as cloud deployed until the backend health endpoint, `/benchmark`, and frontend dashboard are reachable on public URLs.

## GitHub Secrets

- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`
- `AWS_REGION`
- `AWS_S3_BUCKET`
- `EC2_HOST`
- `EC2_USER`
- `EC2_SSH_KEY`
