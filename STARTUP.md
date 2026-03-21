# SRS Engine — Startup Guide

## Prerequisites

Make sure the following are installed before starting:

- Python 3.11+
- Docker Desktop (running)
- MongoDB (running locally on port 27017)

Install Python dependencies:

```bash
pip install -r requirements.txt
pip install aio-pika
```

---

## Environment Setup

Copy `.env.example` to `.env` and fill in your values:

```bash
cp .env.example .env
```

The minimum required values to get running:

```env
GROQ_API_KEY         = your_groq_api_key
SESSION_SECRET_KEY   = any_long_random_string

MONGODB_URI          = mongodb://localhost:27017
MONGODB_DB           = srs_engine

RABBITMQ_HOST        = localhost
RABBITMQ_PORT        = 5672
RABBITMQ_USER        = guest
RABBITMQ_PASSWORD    = guest
RABBITMQ_VHOST       = /
RABBITMQ_SRS_QUEUE   = srs_generation

SMTP_HOST            = your_smtp_host
SMTP_PORT            = 587
SMTP_USERNAME        = your_email@example.com
SMTP_PASSWORD        = your_smtp_password
SMTP_FROM_EMAIL      = your_email@example.com
SMTP_TO_EMAIL        = your_email@example.com
```

---

## Starting the Application

Open **three separate terminals** and run the following commands **in order**.  
Wait for each step to fully start before moving to the next.

---

### Terminal 1 — RabbitMQ

```bash
docker run -it --rm --name rabbitmq -p 5672:5672 -p 15672:15672 rabbitmq:4-management
```

**Wait for this line before proceeding:**
```
Server startup complete
```

> You can monitor the queue visually at **http://localhost:15672**
> Login: `guest` / `guest`
> Go to **Queues tab → srs_generation** to watch messages flow in real time.

---

### Terminal 2 — FastAPI App

```bash
cd C:\SRS_Engine
uvicorn srs_engine.main:app --reload --port 8000
```

**Wait for these lines before proceeding:**
```
Startup | Initializing MongoDB connection
Startup | Connecting to RabbitMQ
RabbitMQ | Queue declared | queue=srs_generation
Startup | RabbitMQ ready
```

> App is now available at **http://localhost:8000**

---

### Terminal 3 — Worker Process

```bash
cd C:\SRS_Engine
python -m srs_engine.worker
```

**You should see:**
```
Worker | Starting up | queue=srs_generation
Consumer | Connecting | host=localhost port=5672 queue=srs_generation
Consumer | Waiting for jobs | queue=srs_generation
```

> The worker is now idle and waiting. It will activate the moment a user clicks **Generate SRS**.

---

## What Happens When You Generate an SRS

| Step | What happens | Where to see it |
|------|-------------|-----------------|
| 1 | User submits the SRS form | Browser redirects to `/jobs` |
| 2 | FastAPI creates a job in MongoDB and publishes to RabbitMQ | Terminal 2 logs |
| 3 | Worker picks up the job | Terminal 3 logs |
| 4 | Phase 1 — 5 AI agents run in parallel | Job card progress bar: 20% |
| 5 | 60 second wait (API rate limit) | Progress pauses at ~35% |
| 6 | Phase 2 — Glossary + Assumptions agents | Progress: 55–60% |
| 7 | 4 Mermaid diagrams rendered | Progress: 75% |
| 8 | Word document (.docx) built | Progress: 90% |
| 9 | Job marked complete in MongoDB | Progress: 100%, download button appears |
| 10 | Email with .docx attachment sent to user | User inbox |

Total generation time: **~3–4 minutes** per document.

---

## Scaling (Multiple Users)

To handle multiple simultaneous users, open additional terminal windows and run the worker command again in each one. RabbitMQ distributes jobs one at a time across all running workers.

```bash
# Terminal 3
python -m srs_engine.worker

# Terminal 4
python -m srs_engine.worker

# Terminal 5
python -m srs_engine.worker
```

---

## Monitoring

| Tool | URL | What to watch |
|------|-----|---------------|
| Job Tracker (UI) | http://localhost:8000/jobs | Live progress cards for all jobs |
| RabbitMQ UI | http://localhost:15672 | Queue depth, message rates |
| MongoDB Compass | localhost:27017 | `srs_engine` → `srs_jobs` collection |
| FastAPI logs | Terminal 2 | HTTP requests, publish confirmations |
| Worker logs | Terminal 3 | Pipeline phases, completion, errors |

---

## Stopping

```bash
# Terminal 3 — Worker
Ctrl + C

# Terminal 2 — FastAPI
Ctrl + C

# Terminal 1 — RabbitMQ
Ctrl + C   (container stops and removes itself automatically due to --rm flag)
```

> **Note:** Any jobs that were `processing` when the worker was stopped will remain stuck in that state in MongoDB.
> To reset them, run this in MongoDB Compass or mongosh:
>
> ```js
> db.srs_jobs.updateMany(
>   { status: "processing" },
>   { $set: { status: "failed", error: "Worker restarted", completed_at: new Date() } }
> )
> ```

---

## Common Errors

**`RabbitMQ connection failed` on FastAPI startup**
→ RabbitMQ Docker container is not running. Start Terminal 1 first.

**`Consumer | Waiting for jobs` never appears**
→ Worker can't connect to RabbitMQ. Check `RABBITMQ_HOST` in your `.env`.

**Job stuck at 20% for a long time**
→ The AI agents are waiting on the LLM API. Check Terminal 3 for errors.
→ May also be a Groq API rate limit. Wait and retry.

**`FileNotFoundError` in email logs**
→ The `.docx` was not generated before the email was sent. Check Terminal 3 for generation errors earlier in the same job.

**`SMTP settings are not configured`**
→ Fill in all five `SMTP_*` values in your `.env` file.