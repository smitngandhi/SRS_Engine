# SRS Engine — Architecture Migration Changes

Tracking all file changes made during the migration from the synchronous
request-blocking model to the async job-based architecture (RabbitMQ +
worker processes + SSE progress streaming).

---

## Legend

| Symbol | Meaning |
|--------|---------|
| NEW  | New file created |
| MOD  | Existing file modified |
| TODO | Planned, not yet implemented |

---

## Phase 1 — RabbitMQ Layer (DONE)

Goal: Establish the message bus.

| File | Status | What changed / why |
|------|--------|---------------------|
| srs_engine/core/queue/rabbitmq.py | NEW | RabbitMQManager singleton. Holds one aio_pika robust connection + channel for the FastAPI process lifetime. Exposes connect_rabbitmq() / disconnect_rabbitmq() for main.py lifespan. |
| srs_engine/core/queue/publisher.py | NEW | publish_srs_job(job_id). Publishes {"job_id": "..."} envelope with PERSISTENT delivery so messages survive a broker restart. |
| srs_engine/core/queue/consumer.py | NEW | run_consumer(handler). Standalone async consumer loop for the worker process. ACKs on success, NACKs with requeue=False on failure. No FastAPI imports. |
| srs_engine/core/config.py | MOD | Added 6 Settings fields: rabbitmq_host, rabbitmq_port, rabbitmq_user, rabbitmq_password, rabbitmq_vhost, rabbitmq_srs_queue. |
| srs_engine/main.py | MOD | Wired connect_rabbitmq() into lifespan startup and disconnect_rabbitmq() into shutdown. Stores manager on app.state.rabbitmq. Startup failure logs error but does NOT crash the app. |
| .env.example | MOD | Added 6 RABBITMQ_* vars with default values. |

New dependency: pip install aio-pika

---

## Phase 2 — Job Model & MongoDB Repository (DONE)

Goal: Persist job state in MongoDB as the single source of truth.

| File | Status | What changed / why |
|------|--------|---------------------|
| srs_engine/core/db/job_model.py | NEW | JobStatus enum (pending, processing, completed, failed). JobStep enum — human-readable phase labels written to current_step. |
| srs_engine/core/db/job_repo.py | NEW | JobRepo class. Methods: create_job() returns UUID; get_by_job_id(); get_jobs_by_user(); update_progress(); mark_completed(); mark_failed(). |
| srs_engine/core/db/mongo.py | MOD | Added 3 indexes for srs_jobs: unique on job_id; compound (user_id, created_at DESC); single-field status. |

---

## Phase 3 — API Changes (DONE)

Goal: POST /generate_srs returns job_id immediately. Added SSE endpoint.

| File | Status | What changed / why |
|------|--------|---------------------|
| srs_engine/core/routers/srs_api.py | MOD | POST /generate_srs rewritten — creates job, publishes to RabbitMQ, returns {"job_id", "status", "message"} immediately. Added GET /job/{job_id}/status (one-shot polling). Added GET /job/{job_id}/status/stream (SSE — polls MongoDB every 1s, pushes events until terminal state). Both new endpoints enforce user ownership (403 otherwise). |
| srs_engine/core/services/srs_service.py | MOD | generate_srs() except block changed from HTTPException wrapping to bare raise — HTTPException is a FastAPI concept and would be mishandled by the worker. Router no longer imports generate_srs. |

Key decisions:
  - RabbitMQ check happens AFTER job creation. If broker is down, job is immediately
    marked failed — no orphaned pending jobs.
  - _serialize_job() strips _id and payload before sending to client.
  - SSE headers include X-Accel-Buffering: no to prevent nginx buffering.

---

## Phase 4 — Worker Process + Email (DONE)

Goal: Standalone worker that runs the pipeline and reports progress to MongoDB.
User receives email on completion.

| File | Status | What changed / why |
|------|--------|---------------------|
| srs_engine/worker.py | NEW | Entry point: python -m srs_engine.worker. handle_job() fetches payload from MongoDB, calls generate_srs() with on_progress callback that writes to JobRepo, calls mark_completed() or mark_failed(). Email sent after completion. Email failures are logged but never fail the job. Worker creates its own Motor connection and InMemorySessionService — no FastAPI app required. _make_app() wraps SimpleNamespace to satisfy get_session_service(app). |
| srs_engine/core/services/srs_service.py | MOD | Added optional on_progress: ProgressCallback = None parameter to generate_srs(). Calls on_progress at 5 checkpoints: 10% (loading agents), 20% (phase 1 start), 55% (phase 2 start), 75% (diagrams), 90% (building doc). Defaults to _noop_progress so all callers without progress reporting are unaffected. |
| srs_engine/core/services/email_service.py | MOD | Added send_srs_complete_email(settings, to_email, user_display_name, project_name, download_url). Same _send_smtp / run_in_threadpool pattern as send_contact_email. Skips silently if to_email is None/empty. |

Progress checkpoint map:
  5%   Picked up by worker              (LOADING_AGENTS)
  10%  Agents loaded                    (generate_srs on_progress)
  20%  Phase 1 agents running           (generate_srs on_progress)
  55%  Phase 2 agents running           (generate_srs on_progress)
  75%  Rendering diagrams               (generate_srs on_progress)
  90%  Building Word document           (generate_srs on_progress)
  100% mark_completed()                 (JobRepo)

Scaling: run multiple workers with the same command. RabbitMQ distributes
jobs across all workers with prefetch_count=1.

---

## Files Touched — Full Summary

SRS_Engine/
  .env.example                            MOD  RabbitMQ vars added
  srs_engine/
    main.py                               MOD  RabbitMQ wired into lifespan
    worker.py                             NEW  Standalone worker entry point
    core/
      config.py                           MOD  RabbitMQ settings added
      db/
        mongo.py                          MOD  srs_jobs indexes added
        job_model.py                      NEW  JobStatus + JobStep enums
        job_repo.py                       NEW  Full CRUD for srs_jobs collection
      queue/
        rabbitmq.py                       NEW  Connection manager singleton
        publisher.py                      NEW  publish_srs_job()
        consumer.py                       NEW  run_consumer() loop
      routers/
        srs_api.py                        MOD  Non-blocking generate_srs + SSE stream
      services/
        srs_service.py                    MOD  on_progress callback + re-raise fix
        email_service.py                  MOD  send_srs_complete_email() added