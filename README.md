# Internal Utility Service

## Project Overview
The Internal Utility Service is a Flask-based REST API that provides utility endpoints for internal use. It solves the problem of deploying a reliable, secure, and automated internal tool by leveraging Docker containerisation, GitHub Actions CI/CD, and AWS EC2 cloud infrastructure. The tech stack includes Python/Flask, Docker, GitHub Actions, AWS EC2, Nginx, and Let's Encrypt.

---

## Architecture Diagram
Developer → GitHub → GitHub Actions Pipeline → Docker Hub → AWS EC2
↓
Nginx (HTTPS)
↓
Flask Container (port 5000)
↓
AWS Secrets Manager (runtime secrets)
**Flow of a code change:**
1. Developer pushes code to GitHub
2. GitHub Actions triggers automatically
3. Pipeline runs tests → lints code → builds Docker image → pushes to Docker Hub
4. Pipeline SSHs into EC2 and deploys new container
5. Nginx receives HTTPS traffic and forwards to Flask container on port 5000
6. App reads secrets from AWS Secrets Manager at runtime

---

## Dockerfile Structure
The Dockerfile uses a **multi-stage build** with two stages:

**Stage 1 — Builder:**
- Base image: `python:3.11-slim`
- Copies `requirements.txt` and installs all Python dependencies
- This stage is discarded after building — it is never part of the final image

**Stage 2 — Runtime:**
- Base image: `python:3.11-slim` (fresh, clean)
- Creates a non-root user `appuser` for security
- Copies only the installed packages from Stage 1
- Copies only `app.py` — no tests, no git history
- Runs as non-root user
- Exposes port 5000
- Includes a HEALTHCHECK that pings `/health` every 30 seconds

---

## Multi-Stage Build Reasoning
A single-stage build would include all build tools, compilers, and intermediate files in the final image — making it 300-500MB+. The multi-stage approach produces a final image of ~100-150MB because only the runtime dependencies and application code are included. This has two key benefits:
- **Size:** Smaller images pull faster and use less storage
- **Security:** Fewer tools in the image means a smaller attack surface — if the container is compromised, the attacker has fewer tools available

---

## CI Workflow Logic
The pipeline is defined in `.github/workflows/ci-cd.yml` and has 3 jobs:

**Job 1 — test (runs on every push and PR):**
- Installs Python dependencies
- Runs `flake8` to lint `app.py` and `test_app.py`
- Runs `pytest` to execute all 8 tests
- If this job fails, the pipeline stops — broken code cannot be built or deployed

**Job 2 — build-and-push (runs only on main, only if Job 1 passed):**
- Builds the multi-stage Docker image
- Pushes the image to Docker Hub with 3 tags: `latest`, semantic version, and git SHA

**Job 3 — deploy (runs only on main, only if Job 2 succeeded):**
- SSHs into EC2 using stored credentials
- Pulls the new image from Docker Hub
- Stops the old container and starts the new one
- Verifies the app is healthy via `/health` endpoint

---

## Tagging Strategy
Every Docker image is pushed with 3 tags:

| Tag | Example | Purpose |
|-----|---------|---------|
| latest | `charlie82610/capstone-app:latest` | Always points to most recent stable build. EC2 pulls this. |
| Semantic Version | `charlie82610/capstone-app:v1.0.8` | Pinnable version number for rollbacks |
| Git SHA | `charlie82610/capstone-app:abc1234` | Traces every image back to the exact commit that built it |

Using all three ensures flexibility: `latest` for automated deployments, semantic versions for controlled releases, and SHA tags for full traceability and auditing.

---

## Secret Injection Strategy
This project uses two separate secret vaults:

**GitHub Secrets (CI/CD secrets):**
- Used by GitHub Actions during the pipeline
- Stores: `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN`, `EC2_HOST`, `EC2_USER`, `EC2_SSH_KEY`
- These are only needed when code is being built and deployed — not at runtime

**AWS Secrets Manager (runtime secrets):**
- Used by the running Flask application on EC2
- Stores: `APP_SECRET_KEY`, `APP_ENV` under `capstone/app-secrets`
- The app reads these at startup via the `boto3` SDK
- The EC2 instance has an IAM role (`capstone-ec2-role`) that grants read access

The split exists because CI secrets and runtime secrets have different lifecycles, different consumers, and different access patterns. Mixing them in one vault creates unnecessary risk.

---

## Deployment Automation
Every push to `main` triggers a fully automated deployment:
1. GitHub Actions builds and pushes a new Docker image to Docker Hub
2. The pipeline SSHs into EC2 using the `EC2_SSH_KEY` GitHub Secret
3. EC2 pulls the new image, stops the old container, starts the new one
4. The pipeline verifies health before completing

No manual SSH steps are required. The entire process takes ~2 minutes from push to live deployment.

---

## HTTPS Setup
HTTPS is enabled using **Let's Encrypt** certificates obtained via **Certbot**:
- Domain: `capstone-kosio.ddns.net` (free subdomain via No-IP)
- Certbot automatically configured Nginx to serve HTTPS on port 443
- HTTP traffic on port 80 is automatically redirected to HTTPS (301 redirect)
- Certificates expire after 90 days but auto-renew via a systemd timer (`certbot.timer`) that runs every 12 hours and renews if less than 30 days remain

HTTPS matters because it encrypts all traffic between the user and server, preventing eavesdropping and man-in-the-middle attacks.

---

## Update Strategy (Blue-Green Deployment)
The `deploy.sh` script implements a blue-green deployment strategy:
1. The current live container (`capstone-app-blue`) runs on port 5000
2. A new container (`capstone-app-green`) is started on port 5001
3. The health endpoint is checked on port 5001 — if it fails, green is removed and blue keeps running
4. If green is healthy, Nginx is updated to proxy to port 5001
5. The old blue container is stopped and removed
6. Green is renamed to blue for the next deployment

This achieves **zero downtime** because traffic only switches after the new version is verified healthy.

---

## Rollback Method
If a bad deployment occurs:

```bash
# SSH into EC2
ssh -i capstone-key.pem ubuntu@3.85.204.189

# Stop the bad container
docker stop capstone-app-blue
docker rm capstone-app-blue

# Pull and run the previous known good image (use the previous git SHA tag)
docker run -d \
  --name capstone-app-blue \
  --restart unless-stopped \
  -p 5000:5000 \
  charlie82610/capstone-app:PREVIOUS_SHA

# Verify health
curl http://localhost:5000/health
```

---

## Trade-offs Made
- **Single EC2 vs Load Balancer:** Using one EC2 instance is simpler and free tier eligible, but creates a single point of failure. With more budget, an Application Load Balancer with multiple instances would provide true high availability.
- **Docker Hub (public) vs ECR (private):** Docker Hub is free and easy to set up but images are publicly visible. AWS ECR would keep images private and integrate more cleanly with IAM, but adds cost and complexity.
- **No-IP free domain vs custom domain:** The free No-IP domain works for this project but expires and requires renewal. A paid custom domain would be more reliable for production.

---

## Reflection Answers

**1. Why did you structure the Dockerfile the way you did?**
I structured it with two stages to separate the build environment from the runtime environment. The builder stage installs all dependencies, and the runtime stage starts fresh and copies only what is needed to run the app. I also added a non-root user for security and a HEALTHCHECK so Docker can monitor the container automatically.

**2. Why multi-stage — what specific problem does it solve?**
A single-stage build would include pip, build tools, and cached files in the final image, making it 300-500MB+. Multi-stage builds solve this by throwing away the builder stage after use. The final image is ~100-150MB and contains only the app and its runtime dependencies — nothing that was only needed during installation.

**3. Why that tagging strategy (latest + semantic + SHA)?**
Each tag serves a different purpose. `latest` ensures EC2 always pulls the most recent build automatically. Semantic version tags allow pinning to a specific release for controlled rollbacks. Git SHA tags provide full traceability — every image can be traced back to the exact line of code that built it, which is essential for debugging production issues.

**4. Why GitHub Secrets + AWS Secrets Manager split — why not just one?**
GitHub Secrets are only available during the CI/CD pipeline — they cannot be accessed by the running application. AWS Secrets Manager is designed for runtime secret retrieval — the app reads secrets on startup. Using one system for both would either expose runtime secrets to the pipeline unnecessarily or require the app to authenticate with GitHub at runtime, which is not a supported pattern.

**5. How does your deployment avoid downtime?**
The blue-green strategy ensures the old container keeps serving traffic while the new one starts up and passes health checks. Nginx only switches to the new container after it is verified healthy. If the new container fails its health check, it is removed and the old one keeps running — users never experience an outage.

**6. How would you scale to multiple EC2 instances?**
I would place an AWS Application Load Balancer in front of multiple EC2 instances running the same container. The CI/CD pipeline would deploy to each instance in a rolling fashion. A shared database and shared secrets via AWS Secrets Manager would ensure all instances serve consistent data.

**7. What security risks still exist in your setup?**
The EC2 instance has a public IP address directly accessible on port 22 (SSH). Ideally SSH access would be restricted to specific IP addresses or replaced with AWS Systems Manager Session Manager. The Docker Hub repository is public, meaning anyone can pull the image. Moving to AWS ECR with private access would improve this. The No-IP domain also relies on a third party service.

**8. How would you evolve this into Kubernetes?**
I would containerise the app the same way but write a Kubernetes Deployment manifest instead of running docker run manually. The CI/CD pipeline would apply the manifest using kubectl. A Kubernetes Service and Ingress would replace Nginx. Secrets would move to Kubernetes Secrets or remain in AWS Secrets Manager accessed via the AWS Secrets Store CSI driver. Horizontal Pod Autoscaler would handle scaling automatically.

---

## Setup Instructions

### Prerequisites
- Python 3.11+
- Git
- Docker Desktop
- VSCode
- AWS CLI

### Clone & Setup
```bash
git clone https://github.com/KosisochukwuOkafor/Internal-Utility-Service.git
cd Internal-Utility-Service
pip install -r requirements.txt
```

### Running the App Locally
```bash
docker build -t capstone-app:local .
docker run -d -p 5000:5000 --name capstone-test capstone-app:local
curl http://localhost:5000/health
```

### Running Tests
```bash
pytest test_app.py -v
```

### Running the Linter
```bash
flake8 app.py test_app.py
```