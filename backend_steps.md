# SpecForge AI — Backend Steps (B1–B22)

> Do ALL backend steps before any frontend work. Test locally after B22.

---

## B1 — Clean `requirements.txt`

**File:** `requirements.txt`

**Remove these (won't install on Linux / unused):**
- `aio_pika` — replaced by `redis[hiredis]`
- `docling`, `pdfplumber`, `pdfminer.six`, `camelot-py[cv]`, `mammoth`, `pytesseract`, `pdf2image` — Upload Upgrader only, require system binaries
- `docx2pdf` — requires LibreOffice, not used in generation path
- `yfinance` — not used anywhere
- `code-review-graph` — dev tool only
- `faiss-cpu`, `sentence-transformers` — 2-3GB Docker image; graceful fallbacks already exist in code

**Add:**
- `redis[hiredis]` — Redis client with C-optimized parser
- `supervisor` — runs web + worker in one Docker container

**Final `requirements.txt`:**
```
# Core Web Framework
fastapi[standard]
uvicorn[standard]
starlette
itsdangerous
jinja2
python-multipart

# AI & LLM
google-adk
google-generativeai
litellm

# Database
motor
pymongo
aiosqlite

# Redis Queue
redis[hiredis]

# Data Validation
pydantic
typing_extensions

# Auth & Sessions
passlib[bcrypt]
bcrypt==4.0.1
authlib
python-dotenv

# HTTP
requests

# Document Generation
python-docx
jsonschema

# Process Management (Docker)
supervisor
```

---

## B2 — Update `config.py`

**File:** `srs_engine/core/config.py`

**Remove:** All 6 `rabbitmq_*` fields

**Add these fields to `Settings` dataclass:**
```python
# Redis (replaces RabbitMQ)
redis_url: str = _env("REDIS_URL", "redis://localhost:6379") or "redis://localhost:6379"
redis_queue_name: str = _env("REDIS_QUEUE_NAME", "srs_queue") or "srs_queue"

# Beta limits
max_beta_users: int = int(_env("MAX_BETA_USERS", "10") or "10")

# Production mode
production: bool = (_env("PRODUCTION", "false") or "false").lower() == "true"
```

---

## B3 — Create `redis_queue.py` (NEW)

**File:** `srs_engine/core/queue/redis_queue.py`

**Purpose:** Drop-in replacement for `rabbitmq.py` with same interface pattern.

**Key design — RPOPLPUSH Reliable Queue:**
```python
import redis.asyncio as aioredis

class RedisManager:
    def __init__(self):
        self._client = None
        self._settings = get_settings()

    async def connect(self):
        self._client = aioredis.from_url(self._settings.redis_url)
        await self._client.ping()

    async def disconnect(self):
        if self._client:
            await self._client.close()

    @property
    def is_connected(self) -> bool:
        return self._client is not None

    @property
    def client(self):
        return self._client
```

**Also include semaphore helpers** (for diagram/upgrade concurrency):
```python
async def acquire_semaphore(self, name: str, timeout: int = 90) -> bool:
    """Try to acquire a Redis-based semaphore. Returns True if acquired."""
    # SET NX with EX (expiry) — atomic lock
    acquired = await self._client.set(f"sem:{name}", "1", nx=True, ex=timeout)
    return bool(acquired)

async def release_semaphore(self, name: str):
    await self._client.delete(f"sem:{name}")
```

---

## B4 — Rewrite `publisher.py`

**File:** `srs_engine/core/queue/publisher.py`

**Replace entire content.** Old: `aio_pika` publish. New: Redis RPUSH.

```python
async def publish_srs_job(job_id: str) -> None:
    manager = get_redis_manager()
    if not manager.is_connected:
        raise RuntimeError("Redis not connected")
    settings = get_settings()
    await manager.client.rpush(settings.redis_queue_name, job_id)
    logger.info(f"Publisher | Job published | job_id={job_id}")
```

---

## B5 — Rewrite `consumer.py`

**File:** `srs_engine/core/queue/consumer.py`

**Replace entire content.** Use RPOPLPUSH reliable queue pattern:

```python
PROCESSING_QUEUE = "srs_processing"

async def run_consumer(handler, timeout=None):
    settings = get_settings()
    client = aioredis.from_url(settings.redis_url)
    queue = settings.redis_queue_name

    while True:
        # Atomically move job from main queue to processing queue
        job_id = await client.brpoplpush(queue, PROCESSING_QUEUE, timeout=timeout or 0)
        if job_id is None:
            break  # timeout reached

        job_id = job_id.decode() if isinstance(job_id, bytes) else job_id

        try:
            await handler(job_id)
            # Success: remove from processing queue
            await client.lrem(PROCESSING_QUEUE, 1, job_id)
        except Exception:
            # Failure: move back to main queue for retry
            await client.lrem(PROCESSING_QUEUE, 1, job_id)
            await client.lpush(queue, job_id)
            raise
```

**Why RPOPLPUSH:** If worker crashes mid-job, job stays in `srs_processing` list. On restart, recovery logic (Step B9) moves it back.

---

## B6 — Update `queue/__init__.py`

**File:** `srs_engine/core/queue/__init__.py`

Replace all rabbitmq imports with redis:
```python
from .redis_queue import get_redis_manager, connect_redis, disconnect_redis
from .publisher import publish_srs_job
```

---

## B7 — Update `main.py`

**File:** `srs_engine/main.py`

**Changes:**
1. Replace `from ...rabbitmq import ...` → `from ...redis_queue import connect_redis, disconnect_redis, get_redis_manager`
2. In lifespan: `connect_redis()` / `disconnect_redis()` instead of rabbitmq
3. Store `app.state.redis = get_redis_manager()` instead of `app.state.rabbitmq`
4. Add `PRODUCTION` toggle for `https_only`:
```python
app.add_middleware(
    SessionMiddleware,
    secret_key=settings.session_secret_key,
    same_site="lax",
    https_only=settings.production,  # BUG FIX #2: was hardcoded False
)
```
5. Add SMTP startup warning:
```python
if not all([settings.smtp_host, settings.smtp_username, settings.smtp_password]):
    logger.warning("WARNING: SMTP not configured — users will NOT receive email backups")
```

---

## B8 — Fix `globals.py` (BUG FIX #1 — CRITICAL)

**File:** `srs_engine/utils/globals.py`

**Bug:** Line 279-280 imports `ctypes.wintypes` unconditionally — crashes on Linux/Docker.

**Fix:** Move the Windows-specific import inside the `platform.system() == 'Windows'` check:
```python
def render_mermaid_png(mermaid_code: str, output_png: Path):
    import os
    import platform
    # Only import ctypes on Windows
    if platform.system() == 'Windows':
        import ctypes
        from ctypes import wintypes
        # ... Windows short path logic
    # ... rest of function
```

---

## B9 — Update `worker.py` (Startup Recovery)

**File:** `srs_engine/worker.py`

**Add** recovery logic at startup — finds jobs stuck in `processing` and requeues them:

```python
async def _recover_stuck_jobs():
    """On startup, find jobs stuck in PROCESSING > 10 min and requeue."""
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=10)
    stuck = await db.srs_jobs.find({
        "status": JobStatus.PROCESSING,
        "updated_at": {"$lt": cutoff}
    }).to_list(length=100)
    for job in stuck:
        jid = job["job_id"]
        await job_repo.update_progress(jid, 0, JobStep.QUEUED, JobStatus.PENDING)
        redis = get_redis_manager()
        await redis.client.rpush(settings.redis_queue_name, jid)
        logger.info(f"Recovery | Requeued stuck job | job_id={jid}")
```

Call `await _recover_stuck_jobs()` in `main()` before `run_consumer()`.

Also update imports: replace `from ...consumer import run_consumer` (which now uses Redis).

---

## B10 — Update `worker_manager.py`

**File:** `srs_engine/worker_manager.py`

**Changes:**
1. `MAX_WORKERS = 1` (was 4) — Groq 30k TPM rate limit
2. Replace all `aio_pika` queue-depth polling with Redis:
```python
async def monitor_queue():
    client = aioredis.from_url(settings.redis_url)
    while True:
        queue_depth = await client.llen(settings.redis_queue_name)
        # ... same scaling logic but with Redis LLEN
```

---

## B11 — Create `file_storage.py` (NEW — GridFS)

**File:** `srs_engine/core/db/file_storage.py`

**Purpose:** All generated files stored in MongoDB GridFS. Replaces all disk I/O.

**Key functions:**
```python
from motor.motor_asyncio import AsyncIOMotorGridFSBucket

class FileStorage:
    def __init__(self, db):
        self.bucket = AsyncIOMotorGridFSBucket(db)

    async def save_file(self, data: bytes, filename: str, metadata: dict) -> str:
        """Save bytes to GridFS, return file_id as string. Overwrites if exists."""
        # Delete old version if exists
        async for f in self.bucket.find({"metadata": metadata}):
            await self.bucket.delete(f._id)
        file_id = await self.bucket.upload_from_stream(filename, data, metadata=metadata)
        return str(file_id)

    async def get_file(self, metadata: dict) -> bytes | None:
        """Get file bytes from GridFS by metadata match."""
        cursor = self.bucket.find({"metadata": metadata})
        doc = await cursor.to_list(1)
        if not doc:
            return None
        stream = await self.bucket.open_download_stream(doc[0]._id)
        return await stream.read()

    async def list_files(self, metadata_filter: dict) -> list[dict]:
        """List files matching metadata filter."""
        results = []
        async for f in self.bucket.find({"metadata": metadata_filter}):
            results.append({"filename": f.filename, "metadata": f.metadata,
                           "length": f.length, "upload_date": f.upload_date})
        return results

    async def delete_file(self, metadata: dict):
        async for f in self.bucket.find({"metadata": metadata}):
            await self.bucket.delete(f._id)
```

**Metadata convention:**
```python
# DOCX: {"type": "docx", "user_id": "...", "project_name": "..."}
# Sections JSON: {"type": "sections_json", "user_id": "...", "project_name": "..."}
# Meta JSON: {"type": "meta_json", "user_id": "...", "project_name": "..."}
# Version DOCX: {"type": "version_docx", "user_id": "...", "project_name": "...", "version": 1}
# SVG: {"type": "svg", "user_id": "...", "diagram_id": "...", "version": 1}
```

---

## B12 — Update `mongo.py`

**File:** `srs_engine/core/db/mongo.py`

**Add** in `init_mongo()`:
```python
# user_quotas index
await db.user_quotas.create_index("user_id", unique=True)
```

**Add** a `get_file_storage` dependency:
```python
from srs_engine.core.db.file_storage import FileStorage

def get_file_storage(request: Request) -> FileStorage:
    return FileStorage(request.app.state.mongo_db)
```

---

## B13 — Create `quota_repo.py` (NEW)

**File:** `srs_engine/core/db/quota_repo.py`

```python
class QuotaRepo:
    def __init__(self, db):
        self.db = db

    async def check_quota(self, user_id, quota_type, project_name=None, limit=2):
        """Returns True if user is within quota."""
        doc = await self.db.user_quotas.find_one({"user_id": user_id})
        if not doc:
            return True
        if project_name:
            projects = doc.get("projects", {})
            return projects.get(project_name, {}).get(quota_type, 0) < limit
        return doc.get(quota_type, 0) < limit

    async def increment_quota(self, user_id, quota_type, project_name=None):
        """Increment a quota counter."""
        if project_name:
            await self.db.user_quotas.update_one(
                {"user_id": user_id},
                {"$inc": {f"projects.{project_name}.{quota_type}": 1}},
                upsert=True
            )
        else:
            await self.db.user_quotas.update_one(
                {"user_id": user_id},
                {"$inc": {quota_type: 1}},
                upsert=True
            )

    async def get_summary(self, user_id):
        doc = await self.db.user_quotas.find_one({"user_id": user_id}) or {}
        return {
            "docx_count": doc.get("docx_count", 0),
            "docx_limit": 2,
            "projects": doc.get("projects", {})
        }
```

---

## B14 — Update `user_repo.py`

**File:** `srs_engine/core/db/user_repo.py`

**Add:**
```python
async def count_users(self) -> int:
    return await self.db.users.count_documents({})
```

---

## B15 — Update `job_repo.py`

**File:** `srs_engine/core/db/job_repo.py`

**Add:**
```python
async def get_queue_position(self, job_id: str) -> int:
    """How many PENDING jobs were created before this one."""
    job = await self.get_by_job_id(job_id)
    if not job or job.get("status") != JobStatus.PENDING:
        return 0
    count = await self.db.srs_jobs.count_documents({
        "status": JobStatus.PENDING,
        "created_at": {"$lt": job["created_at"]}
    })
    return count + 1  # 1-based position
```

---

## B16 — Update `auth.py` (Beta Cap)

**File:** `srs_engine/core/routers/auth.py`

**In `register()` — add before username validation:**
```python
repo = UserRepo(db)
user_count = await repo.count_users()
if user_count >= get_settings().max_beta_users:
    return _redirect_error("/login", "SpecForge AI is in closed beta. All spots are taken — join our waitlist!")
```

**In `google_callback()` — add before `upsert_google_user()`:**
```python
# Only enforce cap for NEW users
existing = await repo.get_by_google_sub(google_sub) or (email and await repo.get_by_email(email))
if not existing:
    user_count = await repo.count_users()
    if user_count >= get_settings().max_beta_users:
        return _redirect_error("/login", "SpecForge AI is in closed beta. All spots are taken — join our waitlist!")
```

---

## B17 — Update `srs_service.py` (GridFS Upload)

**File:** `srs_engine/core/services/srs_service.py`

**After** `generate_srs_document()` returns `generated_path` (Phase 4, ~line 407):

```python
# Upload DOCX to GridFS for persistence
from srs_engine.core.db.file_storage import FileStorage
fs = FileStorage(db)  # db passed via worker
with open(generated_path, "rb") as f:
    await fs.save_file(f.read(), f"{project_name}_SRS.docx",
        {"type": "docx", "user_id": user_id, "project_name": project_name})
```

**In `_save_generated_srs_json()`** — after writing sections + meta to disk, also save to GridFS:
```python
import json
await fs.save_file(json.dumps(sections).encode(), f"{project_name}_sections.json",
    {"type": "sections_json", "user_id": user_id, "project_name": project_name})
await fs.save_file(json.dumps(meta).encode(), f"{project_name}_meta.json",
    {"type": "meta_json", "user_id": user_id, "project_name": project_name})
```

**Note:** `generate_srs()` needs the `db` parameter added. The worker already has `db` — pass it through.

---

## B18 — Update `generated_srs_upgrade_service.py` (GridFS Read/Write)

**File:** `srs_engine/core/services/generated_srs_upgrade_service.py`

**Strategy:** Keep disk as a write-through cache. Primary read from GridFS, write to both.

**Add helper:**
```python
async def _load_json_gridfs(db, user_id, project_name, file_type):
    fs = FileStorage(db)
    data = await fs.get_file({"type": file_type, "user_id": user_id, "project_name": project_name})
    if data:
        return json.loads(data)
    # Fallback: try disk (for backward compat with pre-GridFS data)
    path = _sections_path(user_id, project_name) if file_type == "sections_json" else _meta_path(user_id, project_name)
    if path.exists():
        return _load_json(path)
    return None
```

**Update all functions** that call `_load_json` to use `_load_json_gridfs` and pass `db`.

**In `confirm_upgrade()`** — after `_save_json(sections_path, sections)`, also save to GridFS.

**In `_create_version_backup()`** — also upload version DOCX backup to GridFS.

**In `list_generated_srs()`** — query GridFS metadata instead of disk glob:
```python
async def list_generated_srs(user_id, db=None):
    if db:
        fs = FileStorage(db)
        files = await fs.list_files({"type": "meta_json", "user_id": user_id})
        results = []
        for f in files:
            data = await fs.get_file(f["metadata"])
            meta = json.loads(data) if data else {}
            meta["id"] = meta.get("project_name", "")
            results.append(meta)
        return results
    # disk fallback (local dev)
    ...
```

---

## B19 — Update `diagram_service.py` (SVG to GridFS)

**File:** `srs_engine/core/services/diagram_service.py`

**In `_render_svg()`** — after mmdc renders the SVG to disk:
```python
# Upload to GridFS
svg_bytes = disk_path.read_bytes()
await fs.save_file(svg_bytes, disk_path.name,
    {"type": "svg", "user_id": user_id, "diagram_id": diagram_id, "version": version_number})
```

**Change `_svg_url()`** to return API endpoint instead of static path:
```python
def _svg_url(user_id: str, diagram_id: str, version_number: int) -> str:
    return f"/api/diagrams/{diagram_id}/v/{version_number}/svg"
```

---

## B20 — Update `srs_api.py` (Quota + Queue Position)

**File:** `srs_engine/core/routers/srs_api.py`

**In `POST /generate_srs`:**
```python
# 1. Check quota
quota = QuotaRepo(db)
allowed = await quota.check_quota(user_id, "docx_count", limit=2)
if not allowed:
    raise HTTPException(429, detail="You've reached your free plan limit of 2 SRS documents.")

# 2. Replace RabbitMQ check with Redis check
redis = request.app.state.redis
if redis is None or not redis.is_connected:
    await repo.mark_failed(job_id, "Queue unavailable")
    raise HTTPException(503, detail="Generation service temporarily unavailable.")

# 3. Publish
await publish_srs_job(job_id)

# 4. Increment quota
await quota.increment_quota(user_id, "docx_count")

# 5. Return with queue info + email UX
user_email = user.get("email", "")
return {
    "job_id": job_id,
    "status": JobStatus.PENDING,
    "message": f"SRS generation queued for '{project_name}'.",
    "email_delivery": f"We'll email your document to {user_email} when ready. You can close this tab."
}
```

**In `_serialize_job()`** — add queue position:
```python
# Add queue_position for PENDING jobs
queue_pos = 0
if job.get("status") == JobStatus.PENDING:
    queue_pos = await repo.get_queue_position(job.get("job_id"))
return {
    ...existing fields...,
    "queue_position": queue_pos,
}
```

---

## B21 — Update `diagram_router.py` (Quota + Semaphore + SVG Endpoint)

**File:** `srs_engine/core/routers/diagram_router.py`

**In `POST /api/diagrams/generate`:**
```python
# Quota check
quota = QuotaRepo(db)
allowed = await quota.check_quota(user_id, "diagram_count", project_name=body.project_name, limit=2)
if not allowed:
    raise HTTPException(429, detail="You've reached your free plan limit of 2 diagrams for this project.")

# Semaphore (max 1 concurrent Groq call for fast endpoints)
redis = request.app.state.redis
if not await redis.acquire_semaphore(f"groq:{user_id}", timeout=90):
    raise HTTPException(429, detail="Server busy — please retry in a moment.")
try:
    result = await create_diagram(...)
    await quota.increment_quota(user_id, "diagram_count", project_name=body.project_name)
finally:
    await redis.release_semaphore(f"groq:{user_id}")
```

**Add quota API:**
```python
@router.get("/api/my-quota")
async def get_my_quota(user=Depends(require_user), db=Depends(get_db)):
    user_id = str(user.get("_id"))
    quota = QuotaRepo(db)
    return await quota.get_summary(user_id)
```

**Add SVG streaming endpoint:**
```python
@router.get("/api/diagrams/{diagram_id}/v/{version}/svg")
async def get_diagram_svg(diagram_id: str, version: int, user=Depends(require_user), db=Depends(get_db)):
    user_id = str(user.get("_id"))
    fs = FileStorage(db)
    data = await fs.get_file({"type": "svg", "user_id": user_id, "diagram_id": diagram_id, "version": version})
    if not data:
        raise HTTPException(404, detail="Diagram not found")
    return Response(content=data, media_type="image/svg+xml")
```

---

## B22 — Update `pages.py` (GridFS Downloads + /health)

**File:** `srs_engine/core/routers/pages.py`

**Add `/health`:**
```python
@router.get("/health")
async def health():
    return {"status": "ok", "service": "specforge-ai", "version": "1.0.0-beta"}
```

**Update `/api/my-documents`** — read from GridFS:
```python
@router.get("/api/my-documents")
async def get_my_documents(user=Depends(require_user), db=Depends(get_db)):
    user_id = str(user.get("_id"))
    fs = FileStorage(db)
    files = await fs.list_files({"type": "docx", "user_id": user_id})
    documents = []
    for f in files:
        project_name = f["metadata"].get("project_name", "")
        documents.append({
            "id": f"{project_name}_SRS",
            "project_name": project_name,
            "filename": f.get("filename", f"{project_name}_SRS.docx"),
            "created_at": f.get("upload_date", "").timestamp() if f.get("upload_date") else 0,
            "size_kb": round(f.get("length", 0) / 1024, 1),
        })
    return sorted(documents, key=lambda x: x["created_at"], reverse=True)
```

**Update `/api/download-srs/{doc_id}`** — stream from GridFS:
```python
@router.get("/api/download-srs/{doc_id}")
async def download_srs(doc_id: str, user=Depends(require_user), db=Depends(get_db)):
    user_id = str(user.get("_id"))
    project_name = doc_id.removesuffix("_SRS")
    fs = FileStorage(db)
    data = await fs.get_file({"type": "docx", "user_id": user_id, "project_name": project_name})
    if not data:
        raise HTTPException(404, detail="Document not found")
    return Response(content=data,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers={"Content-Disposition": f'attachment; filename="{doc_id}.docx"'})
```

---

## Local Test Checklist (After B22)

```
□ Install redis locally: docker run -p 6379:6379 redis:alpine
□ Run: uvicorn srs_engine.main:app --reload
□ Run: python -m srs_engine.worker (in separate terminal)
□ Register a user → success
□ Register 11th user → "beta is full" message
□ Generate SRS → job created, SSE progress works, DOCX downloads
□ Restart server → /api/my-documents still returns documents (GridFS)
□ Download after restart → still works
□ 3rd SRS generation → HTTP 429
□ Diagram Studio → generate 2 diagrams → 3rd blocked
□ Section Upgrader → upgrade 2 sections → 3rd blocked
```
