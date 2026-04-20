# 📋 SRS ENGINE - DETAILED PLAN: BUGS, REVENUE & DEPLOYMENT

**Date**: April 20, 2026
**Status**: PLANNING PHASE (Not Implemented Yet)
**Current Tech Stack**: FastAPI + MongoDB + RabbitMQ + Groq API

---

## 🔴 PART 1: CRITICAL BUGS ANALYSIS

### BUG #1: Hardcoded Email Address (CRITICAL - SECURITY)

**Location**: `srs_engine/core/config.py:36`

```python
smtp_to_email: str = _env("SMTP_TO_EMAIL", "smitgandhi585@gmail.com") or "smitgandhi585@gmail.com"
```

**Problem**:

- Default hardcoded to personal email
- ALL users' SRS sent to your email instead of theirs
- Cannot change without modifying code
- Privacy/data leak risk

**Impact**: 🔴 CRITICAL

- Users don't receive their documents
- Your inbox flooded with thousands of PDFs
- Breaks monetization (customers can't get their product)

**Fix Required**:

```python
# BEFORE: Has default
smtp_to_email: str = _env("SMTP_TO_EMAIL", "smitgandhi585@gmail.com") or "smitgandhi585@gmail.com"

# AFTER: Requires env var, no default
smtp_to_email: str | None = _env("SMTP_TO_EMAIL")
```

---

### BUG #2: Weak Session Secret Key (CRITICAL - PRODUCTION)

**Location**: `srs_engine/core/config.py:20`

```python
session_secret_key: str = _env("SESSION_SECRET_KEY", "dev-insecure-change-me") or "dev-insecure-change-me"
```

**Problem**:

- Default secret is weak and exposed
- Session cookies can be forged
- OAuth state validation compromised
- Attacker can hijack user sessions

**Impact**: 🔴 CRITICAL

- Users can login as other users
- Admin accounts can be compromised
- All user data at risk

**Fix Required**:

```python
# BEFORE: Weak default
session_secret_key: str = _env("SESSION_SECRET_KEY", "dev-insecure-change-me") or "dev-insecure-change-me"

# AFTER: Require strong secret from env
session_secret_key: str | None = _env("SESSION_SECRET_KEY")
# Then validate at startup that it's 32+ characters
```

---

### BUG #3: Secrets Exposed in Git (.env in repo)

**Location**: `.env` file checked into git

```
GROQ_API_KEY = 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  ❌ EXPOSED
MONGODB_URI = mongodb+srv://srs_engine_user:srs_engine_123456@...  ❌ EXPOSED
GOOGLE_OAUTH_CLIENT_SECRET = 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  ❌ EXPOSED
SMTP_PASSWORD = gtqp sves cufe rmjw  ❌ EXPOSED
```

**Problem**:

- All secrets visible in git history
- Anyone with repo access has API keys
- Attackers can use your Groq API quota
- Database credentials exposed

**Impact**: 🔴 CRITICAL

- Groq API key compromised
- MongoDB password compromised
- OAuth credentials compromised
- Email account hijacked

**Fix Required**:

1. Add `.env` to `.gitignore` ✓ (already there)
2. Rotate ALL secrets immediately:
   - Generate new Groq API key
   - Change MongoDB password
   - Regenerate OAuth credentials
   - Change Gmail app password
3. Add `.env.example` with placeholders
4. Create interactive setup script

---

### BUG #4: RabbitMQ Fails Silently (HIGH)

**Location**: `srs_engine/main.py:30-40`

```python
try:
    await connect_rabbitmq()
    app.state.rabbitmq = get_rabbitmq_manager()
except Exception as exc:
    logger.error(f"RabbitMQ connection failed | error={exc}")
    app.state.rabbitmq = None  # ❌ Jobs will FAIL at runtime!
```

**Problem**:

- App starts even if RabbitMQ fails
- Job submission succeeds but hangs forever
- User sees "Processing..." that never completes
- No error returned to frontend

**Impact**: 🟠 HIGH

- Users submit jobs → never complete
- No error message → confusion
- Worker process never gets the job
- Support tickets pile up

**Fix Required**:

```python
# Check if RabbitMQ before accepting jobs
@router.post("/api/srs/generate")
async def create_job(request: Request):
    if not request.app.state.rabbitmq:
        raise HTTPException(503, "Job queue unavailable. Please try again in 5 minutes.")
```

---

### BUG #5: No Environment Variable Validation (HIGH)

**Location**: `srs_engine/main.py` startup

```python
# ❌ No validation - just loads defaults
app = create_app()  # Fails only when endpoint is called!
```

**Problem**:

- App starts without critical env vars
- Failures happen at runtime (when users use it)
- Hard to debug what's missing
- Generic error messages to users

**Impact**: 🟠 HIGH

- GROQ_API_KEY missing → LLM calls fail at 20% progress
- SMTP credentials missing → email fails after generation
- MongoDB missing → DB calls fail randomly
- Users see "Something went wrong" with no detail

**Fix Required**:

```python
def validate_required_env() -> None:
    required = [
        "GROQ_API_KEY",
        "SESSION_SECRET_KEY",
        "MONGODB_URI",
        "SMTP_HOST",
        "SMTP_USERNAME",
        "SMTP_PASSWORD",
    ]
    missing = [k for k in required if not os.getenv(k)]
    if missing:
        raise ValueError(f"❌ Missing required env vars: {', '.join(missing)}")

# Call at startup
validate_required_env()
```

---

### BUG #6: No Rate Limiting (HIGH - MONETIZATION BLOCKER)

**Location**: All API endpoints

```python
@router.post("/api/srs/generate")
async def create_job(request: Request):
    # ❌ ANYONE can submit unlimited jobs
    # No auth check, no rate limit
```

**Problem**:

- Unlimited free tier = users generate 1000s of SRS
- Groq API costs skyrocket
- No way to enforce tier limits (Free vs Pro)
- Can't monetize if unlimited

**Impact**: 🔴 CRITICAL FOR MONETIZATION

- Free tier users generate unlimited SRS
- Your Groq bill becomes massive
- Can't charge for product if it's free
- Bots/competitors abuse your API

**Fix Required**: Add rate limiting per user/tier

```python
# Free tier: 1 SRS/month
# Pro tier: 10 SRS/month
# Enterprise: unlimited

# Middleware to check usage:
@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    user_id = request.session.get("user_id")
    tier = get_user_tier(user_id)  # free, pro, enterprise
    usage = get_month_usage(user_id)
    limits = {"free": 1, "pro": 10, "enterprise": 999999}
  
    if usage >= limits[tier]:
        return JSONResponse(
            {"error": f"Limit reached. Upgrade to {tier} tier."},
            status_code=429
        )
    return await call_next(request)
```

---

### BUG #7: No Form Input Validation (MEDIUM)

**Location**: `srs_engine/core/routers/srs_api.py`

```python
# ❌ User input not sanitized
user_input = request.form.get("problem_statement")  # Raw input to LLM!
```

**Problem**:

- Users can inject malicious prompts
- XSS attacks possible
- LLM injection attacks

**Impact**: 🟡 MEDIUM

- [ ] Bad UX (garbage SRS generated)
- [ ] Security vulnerability

**Fix Required**: Add Pydantic validation + sanitization

---

### BUG #8: Mermaid Diagram Windows Path Issue (MEDIUM)

**Location**: `srs_engine/core/services/diagram_service.py`

```python
# ❌ mmdc command fails on Windows without hard-coded path
result = subprocess.run(["mmdc", "-i", mmd_file, "-o", png_file])
```

**Problem**:

- Windows users: diagrams don't generate
- Job completes but missing diagrams in DOCX

**Impact**: 🟡 MEDIUM

- Incomplete documents for Windows users
- Support requests about missing diagrams

**Fix Required**: Auto-detect mmdc path cross-platform

---

### BUG #9: No Error Recovery for Worker (MEDIUM)

**Location**: `srs_engine/worker.py`

```python
# ❌ If LLM fails, job stuck forever
progress = 0
for step in steps:
    progress += 25
    # If this fails: job stuck at current progress
    result = await llm_agent.run()
```

**Problem**:

- Worker crashes = job stuck forever
- User sees "Processing..." indefinitely

**Impact**: 🟡 MEDIUM

- Jobs never complete
- User frustration
- Need manual database cleanup

**Fix Required**: Add timeout + retry logic

---

### BUG #10: No Backup Strategy (MEDIUM)

**Location**: Production data

```
MongoDB Atlas Free Tier
├─ 512MB storage ❌ Will fill up
├─ No automated backups
└─ Single node (no redundancy)
```

**Problem**:

- User data at risk
- No disaster recovery
- GDPR non-compliance

**Impact**: 🟡 MEDIUM

- Data loss if server fails
- Legal liability

**Fix Required**: Setup automated backups

---

## 💰 PART 2: REVENUE GENERATION STRATEGY

### Current State

- ✓ Tech stack working
- ✗ NO payment system
- ✗ NO user tier system
- ✗ NO usage tracking
- ✗ NO monetization

### Revenue Model: SaaS Subscription + Pay-as-You-Go

```
┌────────────────────────────────────────────────────────────┐
│                    PRICING TIERS                           │
├────────────────────────────────────────────────────────────┤
│                                                            │
│ 🆓 FREE TIER                                              │
│ ├─ Cost: $0/month                                        │
│ ├─ Includes: 1 SRS generation/month                      │
│ ├─ Quality: High-level only                              │
│ ├─ Support: Community forum                              │
│ ├─ Goal: User acquisition                                │
│ └─ Convert to Pro: 3-5% expected                         │
│                                                            │
│ 💎 PRO TIER                                               │
│ ├─ Cost: $9.99/month OR $99/year (save $20)            │
│ ├─ Includes: 10 SRS generations/month                    │
│ ├─ Quality: All detail levels (High, Technical, Enterprise)│
│ ├─ Features: Email delivery + archive                    │
│ ├─ Support: Email (24h response)                         │
│ ├─ API: 50 requests/day                                  │
│ ├─ Goal: Main revenue driver                             │
│ └─ Target users: Startups, small consultancies           │
│                                                            │
│ 🏢 ENTERPRISE TIER                                        │
│ ├─ Cost: Custom ($500-5000+/year)                        │
│ ├─ Includes: Unlimited generation                        │
│ ├─ Features: Dedicated support, white-label, API 10k/day │
│ ├─ Support: Slack + phone (2h SLA)                      │
│ ├─ Goal: High-value customers                            │
│ └─ Target users: Large enterprises                       │
│                                                            │
└────────────────────────────────────────────────────────────┘
```

### Revenue Projections (Year 1)

```
Month 1: Launch
├─ Free users: 500
├─ Conversion to Pro: 25 (5%)
├─ Pro MRR: $250
├─ Groq API cost: ~$300
└─ Net: -$50 (acceptable for launch)

Month 3: Growth
├─ Free users: 2000
├─ Pro users: 120 (6%)
├─ Pro MRR: $1,200
├─ Groq API cost: ~$1,500
├─ Enterprise: 0
└─ Net: -$300 (still ramping)

Month 6: Optimization
├─ Free users: 5000
├─ Pro users: 400 (8%)
├─ Enterprise: 2 customers @ $300/mo each
├─ Pro MRR: $4,000
├─ Enterprise MRR: $600
├─ Total MRR: $4,600
├─ Groq API cost: ~$3,000
└─ Net: +$1,600 ✓ PROFITABLE

Year 1 Total: ~$30,000 MRR by year-end
(assuming 10% conversion rate + 5 enterprise customers)
```

### Implementation: 3-Tier System

```python
# 1. USER TIER MODEL
class UserTier(str, Enum):
    FREE = "free"           # 1 SRS/month
    PRO = "pro"            # 10 SRS/month, $9.99/month
    ENTERPRISE = "enterprise"  # unlimited

# 2. USAGE TRACKING
class UsageLog:
    user_id: str
    month: str              # "2026-04"
    srs_count: int
    api_calls: int
    created_at: datetime

# 3. SUBSCRIPTION MODEL
class Subscription:
    user_id: str
    tier: UserTier
    stripe_subscription_id: str
    billing_cycle_start: datetime
    billing_cycle_end: datetime
    status: str  # active, cancelled, past_due
    amount_cents: int  # 999 = $9.99

# 4. PAYMENT GATEWAY: STRIPE
# Free → Sign up with email
# Pro → Stripe checkout → Recurring subscription
# Enterprise → Manual setup + custom invoice
```

### Revenue Collection Flow

```
User Signs Up (Free)
    ↓
Uses 1 SRS/month
    ↓
Wants more → Click "Upgrade"
    ↓
Stripe Checkout loaded
    ↓
User enters card
    ↓
Stripe processes payment
    ↓
Webhook received: subscription_created
    ↓
Set tier to PRO + start billing_cycle
    ↓
User now has 10 SRS/month
    ↓
Each month: Check if cycle ended
    ↓
Auto-renew OR show upgrade prompt
```

---

## 🚀 PART 3: DEPLOYMENT ARCHITECTURE (Zero Cost)

### Target: Deploy on Free Tiers

```
┌─────────────────────────────────────────────────────────────┐
│                   PRODUCTION STACK                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  FRONTEND (Static HTML/JS)                                 │
│  └─ Vercel (Free Tier)                                     │
│     ├─ 100 GB bandwidth/month                              │
│     ├─ Unlimited projects                                  │
│     ├─ Auto-deploy from GitHub                            │
│     ├─ HTTPS + edge caching                               │
│     └─ CDN globally                                        │
│                                                             │
│  BACKEND (FastAPI)                                         │
│  └─ Render (Free Tier)                                     │
│     ├─ 750 CPU-hours/month                                │
│     ├─ Auto-deploy from GitHub                            │
│     ├─ HTTPS included                                      │
│     ├─ Spins down after 15min inactivity                   │
│     └─ Cold start ~30s acceptable                         │
│                                                             │
│  DATABASE (MongoDB)                                        │
│  └─ MongoDB Atlas (Free Tier)                             │
│     ├─ 512 MB storage                                      │
│     ├─ Shared cluster                                      │
│     ├─ Automated backups                                   │
│     └─ HTTPS connection                                    │
│                                                             │
│  MESSAGE QUEUE (RabbitMQ)                                  │
│  └─ CloudAMQP (Free Tier)                                 │
│     ├─ 1 GB RAM                                           │
│     ├─ 1M messages/day limit                              │
│     ├─ Managed (no setup)                                 │
│     └─ AMQP protocol                                       │
│                                                             │
│  BACKGROUND WORKER (SRS Generation)                       │
│  └─ Render Background Workers                            │
│     ├─ 750 CPU-hours/month                               │
│     ├─ Processes queue jobs                              │
│     └─ OR: Self-host on $5/mo VPS                        │
│                                                             │
│  EMAIL DELIVERY                                            │
│  └─ SendGrid (Free Tier)                                 │
│     ├─ 100 emails/day                                     │
│     └─ OR: Gmail SMTP (unlimited)                        │
│                                                             │
│  PAYMENT PROCESSING                                        │
│  └─ Stripe (Free - Pay Per Transaction)                  │
│     ├─ 2.9% + $0.30 per transaction                       │
│     ├─ $9.99 subscription = $0.59 fee                     │
│     ├─ Webhooks + customer management                     │
│     └─ No setup fees                                      │
│                                                             │
│  MONITORING                                                │
│  └─ UptimeRobot (Free)                                   │
│     ├─ 5-minute health checks                             │
│     ├─ Alert on downtime                                  │
│     └─ Email notifications                                │
│                                                             │
│  ANALYTICS & ERRORS                                        │
│  └─ Sentry (Free)                                        │
│     ├─ Error tracking                                     │
│     ├─ Performance monitoring                             │
│     └─ 5000 events/month free                             │
│                                                             │
└─────────────────────────────────────────────────────────────┘

Total Monthly Cost: $0 (all free tiers!)

When Revenue Grows:
├─ Render Starter: +$7/month
├─ MongoDB M0 → M2: +$9/month
├─ CloudAMQP Premium: +$49/month
└─ Total: ~$65/month still very cheap!
```

### Branch Strategy for CI/CD

```
GITHUB REPO STRUCTURE:

main (Production)
├─ Auto-deploys to Vercel (Frontend) + Render (Backend)
├─ Run tests + security checks
├─ Tag releases (v1.0.0, v1.1.0, etc)
└─ Manual promotion from staging

staging (Staging)
├─ Deploys to Render staging app
├─ Full test suite runs
└─ Requires manual approval to promote to main

develop (Development)
├─ All feature PRs merge here
├─ Automated tests run
└─ Developers merge their branches to this

feature/* (Local - Your branch)
├─ feature/add-stripe-payment
├─ feature/fix-rate-limiting
├─ feature/add-email-verification
└─ Create PR to develop
```

### Deployment Flow

```
You push to local branch
    ↓
Create PR to develop branch
    ↓
GitHub Actions tests run
├─ Python unit tests
├─ Lint checks (pylint, black)
├─ Security scan (bandit, safety)
├─ Type checking (mypy)
└─ Build Docker image
    ↓
If all pass → Merge to develop
    ↓
GitHub Actions runs integration tests on staging
    ↓
Smoke tests on staging app
    ↓
If all pass → Create release PR to main
    ↓
You review + approve
    ↓
Merge to main → GitHub Actions runs
├─ All tests again
├─ Build production Docker
├─ Deploy to Vercel (Frontend)
├─ Deploy to Render (Backend)
├─ Run smoke tests on prod
├─ Send Slack notification
└─ ✅ Live!
```

---

## 📝 PART 4: IMPLEMENTATION PLAN

### Phase 1: Bug Fixes (1-2 days)

```
□ Remove hardcoded emails from config.py
□ Remove weak session secret default
□ Add environment variable validation at startup
□ Add RabbitMQ error handling + graceful failure
□ Add rate limiting middleware
□ Add form input validation
□ Regenerate all secrets
□ Add .env.example template
```

### Phase 2: Payment Integration (3-4 days)

```
□ Install Stripe Python SDK
□ Add Stripe API key to .env
□ Create pricing page UI
□ Create user tier model + usage tracking
□ Implement Stripe checkout flow
□ Add subscription webhook handler
□ Create subscription management endpoints
□ Add monthly reset of usage counter
□ Create admin dashboard (view users/revenue)
```

### Phase 3: Interactive Setup (1 day)

```
□ Create setup.py script
□ Ask user for all required env vars
□ Validate each key before saving
□ Create .env file automatically
□ Run dependency checks
```

### Phase 4: CI/CD Pipeline (2-3 days)

```
□ Create GitHub Actions workflow
□ Setup Vercel project
□ Setup Render projects (main + staging)
□ Configure environment secrets
□ Add deployment tests
□ Setup Slack notifications
□ Create deploy documentation
```

### Phase 5: Deployment (1 day)

```
□ Deploy to Vercel (Frontend)
□ Deploy to Render Backend (Staging first)
□ Test everything on staging
□ Deploy to Render Backend (Production)
□ Smoke tests on production
□ Setup monitoring + alerts
□ Update DNS if needed
□ Go live!
```

---

## ✅ PART 5: PRE-IMPLEMENTATION CHECKLIST

Before you say "GO" - verify you have:

```
Infrastructure Credentials:
□ MongoDB Atlas account (free tier created)
□ CloudAMQP account (free instance created)
□ Stripe account (test mode ready)
□ Vercel account (connected to GitHub)
□ Render account (connected to GitHub)
□ GitHub repository access
□ SendGrid OR Gmail account for emails

API Keys Ready:
□ Groq API key (current: gsk_Q08uhY7...)
□ Stripe test key
□ Stripe live key (for production later)

Decisions:
□ Choose free tier or small paid tier for MongoDB?
□ Choose email: SendGrid or Gmail SMTP?
□ Pricing: $9.99/mo or $12.99/mo for Pro?
□ Worker deployment: Render workers or self-host?

Git Setup:
□ .env in .gitignore? (confirm yes)
□ Ready to push to GitHub?
□ Have staging branch setup?
```

---

## 📊 COMPARISON: BEFORE vs AFTER

```
BEFORE (Current):
├─ ✗ Bugs prevent monetization
├─ ✗ No payment system
├─ ✗ No user tiers
├─ ✗ Free forever (no revenue)
├─ ✗ Only works locally
├─ ✗ Manual deployment
└─ ✗ Secrets exposed

AFTER (Planned):
├─ ✓ All bugs fixed
├─ ✓ Stripe payment integration
├─ ✓ Free/Pro/Enterprise tiers
├─ ✓ Recurring revenue ($9.99/mo per user)
├─ ✓ Live on Vercel + Render (globally accessible)
├─ ✓ Auto-deploy with GitHub Actions
├─ ✓ Secrets secured in GitHub Secrets
├─ ✓ Usage tracking (enforce limits)
├─ ✓ Rate limiting (protect from abuse)
├─ ✓ Professional infrastructure
└─ ✓ Ready to scale!
```

---

## 🎯 SUCCESS METRICS

After implementation, you should have:

```
✓ Zero-cost deployment ($0/month on free tiers)
✓ Automated CI/CD (push to main = auto deploy)
✓ 3 revenue tiers (Free, Pro $9.99, Enterprise)
✓ Usage tracking enforced
✓ Rate limiting per user tier
✓ All bugs fixed
✓ Production-ready security
✓ 99.5% uptime target
✓ Email notifications working
✓ Stripe webhooks validated
✓ Monitoring + alerts enabled
```

---

## 🚦 NEXT STEPS

**Your approval needed on:**

1. ✓ Accept bug fixes? (Critical 10 bugs)
2. ✓ Accept $9.99/mo Pro pricing? (or suggest $12.99?)
3. ✓ Accept Stripe for payments? (or Paddle/Gumroad?)
4. ✓ Verify all infrastructure setup (MongoDB, CloudAMQP, etc)?
5. ✓ Ready to proceed with Phase 1 (bugs)?

---

**Reply with:**

```
I APPROVE THIS PLAN

Changes I want:
- [Your feedback]

Let's start with: [Which phase?]
```

OR

```
I HAVE QUESTIONS:
- [Your questions]
```
