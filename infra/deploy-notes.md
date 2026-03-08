# Nautica AI — AWS Deployment Guide

Reference guide for deploying Nautica AI to AWS. This is not automated — follow these steps manually.

---

## Architecture (Production)

```
Internet → ALB → ECS Fargate (frontend container, port 80)
                              ↓ /api proxy
                  ECS Fargate (backend container, port 5002)
                              ↓
                  RDS Postgres (future) / EFS (uploads)
```

---

## Prerequisites

- AWS CLI configured with appropriate IAM permissions
- Docker images pushed to ECR
- VPC with public/private subnets

---

## Step 1: Push Docker Images to ECR

```bash
# Create ECR repositories
aws ecr create-repository --repository-name nautica-frontend
aws ecr create-repository --repository-name nautica-backend

# Login to ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <account-id>.dkr.ecr.us-east-1.amazonaws.com

# Build and push
docker build -t nautica-frontend .
docker tag nautica-frontend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/nautica-frontend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/nautica-frontend:latest

docker build -t nautica-backend ./backend
docker tag nautica-backend:latest <account-id>.dkr.ecr.us-east-1.amazonaws.com/nautica-backend:latest
docker push <account-id>.dkr.ecr.us-east-1.amazonaws.com/nautica-backend:latest
```

---

## Step 2: Create ECS Cluster

```bash
aws ecs create-cluster --cluster-name nautica-cluster
```

---

## Step 3: ECS Task Definition

Create a task definition with two containers (frontend + backend) in a single task, or as separate services.

Key configuration:
- **Frontend container:** port 80, image from ECR
- **Backend container:** port 5002, image from ECR
- **CPU:** 1 vCPU (backend needs compute for YOLO inference)
- **Memory:** 4 GB (YOLO model + OpenCV processing)
- **Environment variables:**
  - `DB_URL` — SQLite path or RDS connection string
  - `UPLOADS_DIR` — EFS mount path or `/app/uploads`
  - `GEMINI_API_KEY` — for AI report generation (optional)

---

## Step 4: Storage

### Current (SQLite + local uploads)
- Mount an EFS volume to the backend container
- SQLite DB file stored on EFS at `/app/data/nautica.db`
- Uploads stored on EFS at `/app/uploads/`

### Future Production Option: RDS Postgres
- Create an RDS Postgres instance in the same VPC
- Update `DB_URL` to: `postgresql://user:pass@rds-endpoint:5432/nautica`
- The backend's `database.py` already handles non-SQLite connection args

### Future Production Option: S3 for Uploads
- Create S3 bucket for uploads
- Modify upload routes to use presigned URLs
- Config already has `S3_UPLOAD_BUCKET` and `S3_RESULTS_BUCKET` placeholders

---

## Step 5: Application Load Balancer

```bash
# Create ALB
aws elbv2 create-load-balancer \
  --name nautica-alb \
  --subnets <subnet-1> <subnet-2> \
  --security-groups <sg-id>

# Create target group for frontend
aws elbv2 create-target-group \
  --name nautica-frontend-tg \
  --protocol HTTP --port 80 \
  --vpc-id <vpc-id> \
  --target-type ip \
  --health-check-path /
```

---

## Step 6: Create ECS Service

```bash
aws ecs create-service \
  --cluster nautica-cluster \
  --service-name nautica-service \
  --task-definition nautica-task \
  --desired-count 1 \
  --launch-type FARGATE \
  --network-configuration "awsvpcConfiguration={subnets=[<subnet>],securityGroups=[<sg>],assignPublicIp=ENABLED}" \
  --load-balancers "targetGroupArn=<tg-arn>,containerName=frontend,containerPort=80"
```

---

## Cost Estimates (us-east-1, small scale)

| Resource | Spec | Estimated Monthly Cost |
|----------|------|----------------------|
| ECS Fargate | 1 vCPU, 4 GB, 1 task | ~$30 |
| ALB | 1 load balancer | ~$16 |
| EFS | 5 GB storage | ~$1.50 |
| ECR | 2 images | ~$1 |
| **Total** | | **~$50/month** |

RDS Postgres (if added): db.t3.micro ~$15/month additional.

---

## Health Check

The backend exposes `GET /api/health` which returns:
```json
{"status": "operational", "version": "0.1.0"}
```

Use this as the health check path for ECS and ALB target groups.
