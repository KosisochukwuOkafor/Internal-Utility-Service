# Getting Started — Internal Utility Service

This guide is for new developers joining the project. Follow these steps to get the app running locally and understand the development workflow.

---

## Prerequisites
Make sure you have the following installed before starting:

| Tool | Version | Download |
|------|---------|----------|
| Python | 3.11+ | https://python.org/downloads |
| Git | Latest | https://git-scm.com/downloads |
| Docker Desktop | Latest | https://www.docker.com/products/docker-desktop |
| VSCode | Latest | https://code.visualstudio.com |
| AWS CLI | Latest | https://aws.amazon.com/cli/ |

**Verify your installations:**
```bash
python --version
git --version
docker --version
aws --version
```

---

## Clone & Setup

```bash
# Clone the repository
git clone https://github.com/KosisochukwuOkafor/Internal-Utility-Service.git

# Navigate into the project folder
cd Internal-Utility-Service

# Install Python dependencies
pip install -r requirements.txt
```

---

## Running the App Locally

**Option 1 — Run with Docker (recommended):**
```bash
# Build the Docker image
docker build -t capstone-app:local .

# Run the container
docker run -d -p 5000:5000 --name capstone-test capstone-app:local

# Test the endpoints
curl http://localhost:5000/health
curl -X POST http://localhost:5000/sum -H "Content-Type: application/json" -d '{"a": 5, "b": 10}'
curl -X POST http://localhost:5000/reverse-string -H "Content-Type: application/json" -d '{"text": "hello"}'

# Stop and remove the container when done
docker stop capstone-test
docker rm capstone-test
```

**Option 2 — Run with Python directly:**
```bash
flask run --host=0.0.0.0 --port=5000
```

---

## Running Tests

```bash
pytest test_app.py -v
```

**What each test checks:**
- `test_health` — GET /health returns HTTP 200
- `test_home` — GET / returns HTTP 200
- `test_users` — GET /users returns HTTP 200
- `test_health_returns_json` — /health response is valid JSON
- `test_home_returns_message` — / response contains a message field
- `test_home_returns_environment` — / response contains environment field
- `test_home_returns_db_host` — / response contains db_host field
- `test_health_status_value` — /health returns {"status": "UP"}

All 8 tests must pass before any code can be merged.

---

## Running the Linter

```bash
flake8 app.py test_app.py
```

**What flake8 checks:**
- PEP 8 style compliance
- Missing whitespace around operators (E225)
- Lines exceeding 79 characters (E501)
- Unused imports (F401)
- Undefined variables (F821)

If flake8 returns no output, your code is clean. Any errors must be fixed before pushing.

---

## Branch Workflow

```bash
# Always start from an up-to-date main branch
git checkout main
git pull origin main

# Create a new feature branch
git checkout -b feature/TRELLO-###-short-description

# Make your changes, then stage and commit
git add .
git commit -m "[TRELLO-###] Short description of what you did"

# Push your branch
git push origin feature/TRELLO-###-short-description
```

**Branch naming format:** `feature/TRELLO-###-short-description`
- Example: `feature/TRELLO-003-add-8th-test`
- Never push directly to `main`

---

## Opening a Pull Request

1. Go to your GitHub repo page
2. Click the yellow banner **"Compare & pull request"** that appears after pushing
3. Set the title to: `[TRELLO-###] Short description`
4. Click **"Create pull request"**
5. Wait for the CI pipeline to run — you will see a green checkmark or red X under the PR
6. Only merge when all checks pass ✅

---

## Troubleshooting

**1. Docker Desktop not running:**

Cannot connect to the Docker daemon

Fix: Open Docker Desktop and wait for the green "running" indicator before retrying.

**2. Permission denied on .pem file (Mac/Linux):**

Permission denied (publickey)
Fix:
```bash
chmod 400 ~/Downloads/capstone-key.pem
```

**3. Flake8 errors blocking the pipeline:**

E225 missing whitespace around operator
Fix: Run `flake8 app.py test_app.py` locally, fix all reported errors, then push again.

**4. AWS credential issues:**

NoCredentialsError: Unable to locate credentials
Fix: Run `aws configure` and enter your AWS Access Key ID, Secret Access Key, and region (`us-east-1`).

**5. Port already in use:**

Error: Address already in use — port 5000
Fix:
```bash
# Find and kill the process using port 5000
# On Windows:
netstat -ano | findstr :5000
taskkill /PID <PID> /F

# On Mac/Linux:
lsof -i :5000
kill -9 <PID>
```