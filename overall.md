# SpecForge AI — MVP Deployment Master Plan

> **Product:** SpecForge AI — Intelligent Multi-Agent Platform for Automated SRS  
> **Beta:** 10 users · $0/month · All features except Upload Upgrader

---

## Architecture

```
Browser → FastAPI (Railway, 1 container via supervisord)
              ├─ uvicorn (web)
              └─ worker.py (SRS generation)
                    ↓                    ↓
            MongoDB Atlas M0       Upstash Redis FREE
            (users, jobs,          (job queue via
             quotas, GridFS         RPOPLPUSH)
             file storage)
```

## What Changes

| Area | Current | After |
|------|---------|-------|
| Queue | RabbitMQ (aio_pika) | Redis RPOPLPUSH (Upstash free) |
| Files | Local disk (lost on restart) | MongoDB GridFS (persistent) |
| Workers | Separate terminal | supervisord in Docker |
| mmdc | Local Node.js | Docker with Node.js 20 + Chromium |
| Users | Unlimited | 10 beta cap (env-configurable) |
| Quotas | None | 2 SRS/user, 2 diagrams/project, 2 upgrades/project |
| Upload Upgrader | Active | Coming Soon page |
| Concurrency | Multiple workers | MAX_WORKERS=1 (Groq 30k TPM limit) |
| Name | SRS_Engine | SpecForge AI |

## Bugs Found

| # | Bug | Severity | Location |
|---|-----|----------|----------|
| 1 | `from ctypes import wintypes` crashes Linux | 🔴 CRITICAL | `globals.py:279` |
| 2 | `https_only=False` in production | 🔴 CRITICAL | `main.py:76` |
| 3 | RabbitMQ required = 503 on all SRS gen | 🔴 CRITICAL | `srs_api.py:122` |
| 4 | Files on disk = lost on redeploy | 🔴 CRITICAL | everywhere |
| 5 | faiss-cpu breaks Docker (2-3GB) | 🔴 CRITICAL | `requirements.txt` |
| 6 | No `/health` for Railway | 🟠 HIGH | missing |
| 7 | Heavy deps won't install on Linux | 🟠 HIGH | `requirements.txt` |
| 8 | SMTP silent failure = lost DOCX | 🟡 MEDIUM | `worker.py` |
| 9 | No user cap or quotas | 🟡 MEDIUM | `auth.py` |

## Phase Summary

| Phase | Doc | Steps | What |
|-------|-----|-------|------|
| Backend | `backend_steps.md` | B1–B22 | Redis, GridFS, quotas, bug fixes |
| Frontend | `frontend_steps.md` | F1–F10 | Coming Soon, quota UI, branding |
| Deploy | `deployment.md` | D1–D12 | Docker, Railway, env vars, smoke test |

## Execution Order

```
Backend (B1–B22) → Local Test → Frontend (F1–F10) → UI Test → Deploy (D1–D12)
```

## Monthly Cost: $0

| Service | Cost |
|---------|------|
| Railway (1 service, free $5 credit) | $0-5 |
| MongoDB Atlas M0 | $0 |
| Upstash Redis free tier | $0 |
| Groq API free tier | $0 |
