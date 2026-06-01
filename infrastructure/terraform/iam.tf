# No EC2 IAM role is required for the current deployment flow.
# Backend deployment uses the operator's local AWS CLI configuration and SSH.
# Add a least-privilege instance profile here only if the backend later needs
# direct S3/model-bucket access from inside EC2.
