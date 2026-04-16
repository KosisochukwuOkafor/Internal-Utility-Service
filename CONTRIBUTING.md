# Contributing — Internal Utility Service

This document defines the rules and workflow every developer must follow when contributing to this project.

---

## Full Development Workflow

1. Pick a Trello card from the **Backlog** column and move it to **In Progress**
2. Create a feature branch from `main` using the correct naming format
3. Make your changes locally
4. Run tests and linter to verify everything passes
5. Commit your changes with the correct commit message format
6. Push your branch and open a Pull Request on GitHub
7. Wait for the CI pipeline to pass — all checks must be green
8. Move your Trello card to **Review/QA**
9. Once approved and CI passes, merge the PR
10. Move your Trello card to **Done**

---

## Branching Rules

**Format:** `feature/TRELLO-###-short-description`

**Examples:**
- `feature/TRELLO-003-add-8th-test`
- `feature/TRELLO-006-add-cicd-pipeline`
- `feature/TRELLO-007-documentation`

**Rules:**
- Always branch off from an up-to-date `main`
- Never push directly to `main` — all changes must go through a Pull Request
- One Trello card = one branch
- Delete the branch after merging

```bash
# Correct way to start a new branch
git checkout main
git pull origin main
git checkout -b feature/TRELLO-###-short-description
```

**Why this rule exists:** Direct pushes to `main` bypass the CI pipeline and code review process. A broken push could deploy bad code directly to production.

---

## Commit Format

**Format:** `[TRELLO-###] Short description of what you did`

**Good examples:**
- `[TRELLO-003] Add 8th pytest test for large number sum`
- `[TRELLO-006] Add CI/CD pipeline with test, build, and deploy jobs`
- `[TRELLO-007] Add README with architecture and reflection answers`

**Bad examples:**
- `fixed stuff`
- `update`
- `WIP`
- `changes`

**Rules:**
- Always reference the Trello card number
- Use present tense — "Add" not "Added"
- Keep it under 72 characters
- Be specific — describe what changed, not how

---

## Pull Request Process

**Title format:** `[TRELLO-###] Short description`

**What to write in the PR description:**
- What this PR does
- Which Trello card it relates to
- Any testing notes or screenshots if relevant

**CI requirements:**
- All 3 pipeline jobs must pass: Run Tests & Lint → Build & Push Image → Deploy to EC2
- The `Run Tests & Lint` check is required — PRs cannot be merged if it fails
- Never merge a PR with a red X on any check

**Who can merge:**
- The author can merge their own PR after CI passes
- For team projects, at least one reviewer approval is required before merging

---

## CI/CD Pipeline Explanation

The pipeline has 3 jobs that run in sequence:

**Job 1 — Run Tests & Lint:**
- Runs on every push and every PR
- Installs dependencies, runs `flake8`, runs `pytest`
- If this fails, the pipeline stops — the PR cannot be merged

**Job 2 — Build & Push Image:**
- Runs only on pushes to `main`
- Only runs if Job 1 passed
- Builds the Docker image and pushes to Docker Hub with 3 tags

**Job 3 — Deploy to EC2:**
- Runs only on pushes to `main`
- Only runs if Job 2 succeeded
- SSHs into EC2, pulls the new image, restarts the container, verifies health

**What to do when the pipeline fails:**
1. Click the red X on GitHub to open the Actions log
2. Read the error message — it will tell you exactly which step failed
3. Fix the issue locally
4. Push a new commit — the pipeline will re-run automatically

---

## Secrets Policy

**Golden Rule: Never commit secrets to the repository.**

- Never put passwords, API keys, tokens, or .pem files in your code
- Never put secrets in the Dockerfile or docker-compose files
- Never put secrets in commit messages
- If you accidentally commit a secret, it is compromised — rotate it immediately even if you delete it, because it exists in git history forever

**How secrets are managed in this project:**

| Secret | Location | Used by |
|--------|----------|---------|
| DOCKERHUB_USERNAME | GitHub Secrets | CI/CD pipeline |
| DOCKERHUB_TOKEN | GitHub Secrets | CI/CD pipeline |
| EC2_HOST | GitHub Secrets | CI/CD pipeline |
| EC2_USER | GitHub Secrets | CI/CD pipeline |
| EC2_SSH_KEY | GitHub Secrets | CI/CD pipeline |
| APP_SECRET_KEY | AWS Secrets Manager | Running app on EC2 |
| APP_ENV | AWS Secrets Manager | Running app on EC2 |

**How to add a new secret:**
- For CI/CD secrets: GitHub repo → Settings → Secrets and variables → Actions → New repository secret
- For runtime secrets: AWS Console → Secrets Manager → capstone/app-secrets → Edit

---

## Coding Standards

- Follow **PEP 8** — the official Python style guide
- Maximum line length: **79 characters**
- Use **snake_case** for function and variable names
- Use **UPPER_CASE** for constants
- Add a docstring to every function that isn't self-explanatory
- Remove all unused imports before committing

**flake8 is enforced in the pipeline** — any style violation will fail the build. Run it locally before pushing:

```bash
flake8 app.py test_app.py
```

---

## Docker Standards

- All Dockerfiles must use **multi-stage builds**
- The runtime stage must run as a **non-root user**
- All Dockerfiles must include a **HEALTHCHECK** instruction
- Never include secrets, .env files, or .pem files in Docker images
- Always include a **.dockerignore** file to exclude unnecessary files

---

## Failure Handling

**If the pipeline fails:**
1. Go to GitHub → Actions tab
2. Click the failed run
3. Expand the failed step to read the error
4. Fix it locally, commit, and push — the pipeline reruns automatically

**If a deployment breaks production:**
1. SSH into EC2
2. Roll back to the previous image using its git SHA tag:
```bash
docker stop capstone-app-blue
docker rm capstone-app-blue
docker run -d --name capstone-app-blue \
  --restart unless-stopped -p 5000:5000 \
  charlie82610/capstone-app:PREVIOUS_SHA
```
3. Verify health: `curl http://localhost:5000/health`
4. Investigate the root cause before pushing a fix

---

## Deployment Strategy

This project uses **blue-green deployment** via `deploy.sh`:

- The current live container runs as `capstone-app-blue` on port 5000
- A new container starts as `capstone-app-green` on port 5001
- Health is verified on the green container before any traffic switch
- Nginx switches traffic to green only after health check passes
- Blue is removed and green is renamed to blue for the next cycle

**Zero downtime** is achieved because users are always served by a healthy container — traffic only switches after the new version is confirmed working.

**To trigger a manual rollback:**
- Stop the current container
- Start a previous image using its Docker Hub SHA tag
- Nginx continues serving on port 5000 with no interruption