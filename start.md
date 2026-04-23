# 🚀 SRS Engine - Complete Startup Guide

## Table of Contents
1. [System Overview](#system-overview)
2. [Prerequisites](#prerequisites)
3. [Installation Steps](#installation-steps)
4. [Configuration](#configuration)
5. [Running the Application](#running-the-application)
6. [Verification Checklist](#verification-checklist)
7. [Troubleshooting](#troubleshooting)

---

## System Overview

**SRS Engine** is an AI-powered Software Requirements Specification (SRS) document generator. It uses specialized AI agents to automatically create professional SRS documents in minutes.

### What It Does:
- ✅ Takes your project information (name, problem statement, features, etc.)
- ✅ Uses AI agents to generate detailed SRS sections
- ✅ Creates architecture diagrams (visual representations)
- ✅ Outputs a professional `.docx` document
- ✅ Stores user accounts and projects in a database

### Technology Stack:
- **Backend**: FastAPI (Python web framework)
- **AI**: Groq API (fast LLM processing)
- **Database**: MongoDB (user & project storage)
- **Frontend**: HTML + JavaScript
- **Diagrams**: Mermaid CLI (generates PNG diagrams)
- **Documents**: python-docx (creates Word documents)

---

## Prerequisites

Before starting, ensure you have:

| Item | Why You Need It | Download |
|------|-----------------|----------|
| **Python 3.10+** | Core runtime | [python.org](https://www.python.org/downloads/) |
| **Node.js (LTS)** | Mermaid CLI dependency | [nodejs.org](https://nodejs.org/) |
| **Git** | Code version control | [git-scm.com](https://git-scm.com/) |
| **Groq API Key** | AI processing (FREE) | [console.groq.com/keys](https://console.groq.com/keys) |
| **MongoDB** | Database (Local or Cloud) | [mongodb.com](https://www.mongodb.com/) |
| **Google OAuth** (Optional) | Social login | [Google Cloud Console](https://console.cloud.google.com/) |

### Obtaining Required Keys:

#### 1. Get Groq API Key (Required)
1. Visit [console.groq.com/keys](https://console.groq.com/keys)
2. Sign up or log in with Google
3. Click "Create API Key"
4. Copy the key (keep it secret!)
5. You'll use this in step: [Configuration](#configuration)

#### 2. Setup MongoDB (Required)
**Option A: Local MongoDB**
- Download from [mongodb.com/try/download/community](https://www.mongodb.com/try/download/community)
- Install and run locally
- Connection string: `mongodb://localhost:27017`

**Option B: MongoDB Atlas (Cloud - Recommended)**
1. Visit [mongodb.com/cloud/atlas](https://www.mongodb.com/cloud/atlas)
2. Sign up (free tier available)
3. Create a cluster
4. Get connection string from Atlas dashboard
5. Use this string in your `.env` file

#### 3. Google OAuth (Optional - Only if you want social login)
1. Go to [console.cloud.google.com](https://console.cloud.google.com/)
2. Create a new project
3. Enable Google OAuth 2.0
4. Create OAuth 2.0 credentials (Web application)
5. Add redirect URI: `http://127.0.0.1:8000/auth/google/callback`
6. Copy Client ID and Client Secret

---

## Installation Steps

### Step 1: Clone the Repository

```bash
git clone https://github.com/smitngandhi/SRS_Engine.git
cd SRS_Engine
```

### Step 2: Create Python Virtual Environment

**On Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**On macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

✅ You should see `(venv)` appear in your terminal prompt.

### Step 3: Install Python Dependencies

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

This installs:
- fastapi (web framework)
- groq (AI API)
- pymongo/motor (database)
- python-docx (document generation)
- And 15+ other dependencies

### Step 4: Install Mermaid CLI (Required for diagrams)

```bash
npm install -g @mermaid-js/mermaid-cli
mmdc --version  # Verify installation
```

**Windows-specific**: You might need to configure the path. See [Troubleshooting](#troubleshooting).

### Step 5: Create `.env` Configuration File

Copy the example file and update it:

```bash
cp .env.example .env
```

Now open `.env` and edit with your actual keys (see [Configuration](#configuration) section).

---

## Configuration

Open the `.env` file in your project root and fill in the values:

### Example `.env` File:

```dotenv
# ============ REQUIRED ============

# Your Groq API Key (get from console.groq.com/keys)
GROQ_API_KEY=gsk_xxxxxxxxxxxxxxxxxxxx
GROQ_MODEL=groq/meta-llama/llama-4-scout-17b-16e-instruct

# MongoDB connection
MONGODB_URI=mongodb+srv://user:password@cluster.mongodb.net
MONGODB_DB=srs_engine

# Session secret (use a long random string)
SESSION_SECRET_KEY=your-very-long-random-secret-key-min-32-chars

# ============ OPTIONAL ============

# For Google OAuth Login (only if you set it up)
GOOGLE_OAUTH_CLIENT_ID=xxxxx.apps.googleusercontent.com
GOOGLE_OAUTH_CLIENT_SECRET=GOCSPX-xxxxxxxxxxxxxx
GOOGLE_OAUTH_REDIRECT_URI=http://127.0.0.1:8000/auth/google/callback

# For email notifications (contact form)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM_EMAIL=your-email@gmail.com
SMTP_TO_EMAIL=recipient@example.com

# Logging
LOG_LEVEL=INFO
LOG_DIR=./logs
```

### What Each Setting Does:

| Setting | Purpose | Example |
|---------|---------|---------|
| `GROQ_API_KEY` | Unlocks AI generation | `gsk_...` |
| `GROQ_MODEL` | Which AI model to use | `groq/meta-llama/...` |
| `MONGODB_URI` | Where to store data | `mongodb://localhost:27017` |
| `MONGODB_DB` | Database name | `srs_engine` |
| `SESSION_SECRET_KEY` | Encrypts user sessions | Any random 32+ char string |
| `GOOGLE_OAUTH_*` | Google login | Your OAuth credentials |
| `SMTP_*` | Email sending | Email account details |
| `LOG_LEVEL` | How verbose logs are | `INFO`, `DEBUG`, `WARNING` |

---

## Running the Application

### Start the Application

```bash
uvicorn srs_engine.main:app --reload
```

### What This Does:
- Starts a web server at `http://127.0.0.1:8000`
- Loads your `.env` configuration
- Connects to MongoDB
- Sets up all API routes
- Initializes logging

### Expected Output:
```
INFO:     Uvicorn running on http://127.0.0.1:8000
INFO:     Application startup complete
```

### Access the Application

Open your browser and go to:
```
http://localhost:8000
```

You should see:
1. **Login Page** (if you're not logged in)
   - Sign up with username/password
   - Or use Google login (if configured)

2. **Home Page** (after login)
   - SRS Generator form
   - Navigation menu
   - Feature options

---

## Verification Checklist

After startup, verify everything works:

### ✅ Quick Verification

1. **Browser Test**
   - Open `http://localhost:8000`
   - Should see login page
   - ✓ If yes, move to next step

2. **Create Account**
   - Click "Sign Up"
   - Create username/password
   - ✓ If successful, move to next step

3. **Access Generator**
   - Click "SRS Generator"
   - Should see form with fields
   - ✓ If form loads, move to next step

4. **Test AI Features**
   - Fill in Project Name and Problem Statement
   - Click "✨ Enhance" button
   - Should see enhanced problem statement in 10-15 seconds
   - ✓ If AI responds, AI layer works!

5. **Generate SRS Document**
   - Fill complete form
   - Click "Generate SRS"
   - Should download `.docx` file in 60-90 seconds
   - ✓ If document created, system works!

### Detailed Verification

#### Check Logs:
```bash
# Watch logs in real-time
tail -f logs/srs_engine.log

# Or Windows:
Get-Content logs/srs_engine.log -Wait
```

#### Test Database Connection:
- MongoDB should have `srs_engine` database
- Check collections: `users`, `projects`, `sessions`

#### Test Groq API:
- If enhancement fails, check Groq API key in `.env`
- Verify you haven't exceeded free tier limits

#### Test Mermaid:
```bash
mmdc --help
mmdc -i test.mmd -o test.png
```

---

## Troubleshooting

### Common Issues and Solutions

#### ❌ "ModuleNotFoundError: No module named 'fastapi'"

**Cause**: Virtual environment not activated or dependencies not installed

**Fix**:
```bash
# Activate virtual environment
Windows: venv\Scripts\activate
macOS/Linux: source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

#### ❌ "Connection refused" (MongoDB)

**Cause**: MongoDB is not running

**Fix**:
```bash
# If using local MongoDB:
# Windows: MongoDB service should auto-run
# macOS: brew services start mongodb-community
# Linux: sudo systemctl start mongod

# If using MongoDB Atlas:
# Check internet connection
# Verify connection string in .env
```

#### ❌ "GROQ_API_KEY not found"

**Cause**: `.env` file not set up or not found

**Fix**:
```bash
# Verify .env exists in root directory
ls .env  # or: dir .env (Windows)

# Check it has your API key
cat .env  # or: type .env (Windows)

# Reload by restarting:
# Stop the server (Ctrl+C) and restart
uvicorn srs_engine.main:app --reload
```

#### ❌ "Mermaid CLI not found"

**Cause**: npm installation failed or path not configured

**Fix**:
```bash
# Reinstall global
npm install -g @mermaid-js/mermaid-cli

# Verify installation
mmdc --version

# Windows only: Update path in globals.py
# Find your mmdc.cmd location:
where mmdc
# Should output: C:\Users\YourName\AppData\Roaming\npm\mmdc.cmd
```

#### ❌ "Database error" or "Connection pool full"

**Cause**: MongoDB connection issue

**Fix**:
```bash
# Test MongoDB connection
# If using Atlas, test in MongoDB Compass:
# Paste connection string
# Should connect successfully
```

#### ❌ "CORS Error" or "POST failed"

**Cause**: Cross-origin issues or server configuration

**Fix**:
```bash
# Make sure you're accessing http://localhost:8000
# Not http://127.0.0.1:8000 in some cases
# Restart server
```

#### ❌ "Enhance button doesn't work"

**Cause**: API endpoint failing silently

**Fix**:
1. Open browser DevTools (F12)
2. Go to Console tab
3. Click Enhance button
4. Check for error messages
5. Verify Groq API key is correct

#### ❌ "Generated document is blank"

**Cause**: AI agents failed to generate content

**Fix**:
- Check Groq API quota (free tier has limits)
- Verify problem statement is detailed enough
- Check logs for AI errors
- Try with simpler project details first

---

## Next Steps

After successful startup:

1. **Learn the Frontend** → Read `startup_guide.md`
   - Understand how the form works
   - See how each button triggers backend

2. **Learn the APIs** → Read `api.md`
   - Understand all endpoints
   - See request/response formats

3. **Customize the System** → Modify agents
   - Add new AI agents
   - Change how documents are generated
   - Add custom requirements

4. **Deployment**
   - Use production-grade server (Gunicorn)
   - Set up HTTPS
   - Configure proper database backups

---

## Getting Help

### Debug Mode
```bash
# Start with debug logging
LOG_LEVEL=DEBUG uvicorn srs_engine.main:app --reload
```

### Logs Location
- Main logs: `./logs/srs_engine.log`
- Each request logged with timestamp
- Errors highlighted clearly

### Common Debug Steps
1. Check `.env` configuration
2. Verify API keys are valid
3. Check internet connection
4. Look at browser console (F12)
5. Check server logs (terminal)
6. Restart server with `Ctrl+C` then rerun

---

## Project Structure Quick Reference

```
SRS_Engine/
├── srs_engine/
│   ├── main.py                 # Entry point
│   ├── core/
│   │   ├── routers/            # API endpoints
│   │   ├── services/           # Business logic
│   │   ├── db/                 # Database setup
│   │   └── auth/               # Authentication
│   ├── agents/                 # AI agents
│   ├── schemas/                # Data validation
│   ├── templates/              # HTML pages
│   └── static/                 # CSS, JS, images
├── requirements.txt            # Dependencies
├── .env.example                # Configuration template
└── .env                        # Your actual config (CREATE THIS)
```

---

## Performance Tips

- **First run is slower** (models loading, compilation)
- **Keep `.env` secret** (never commit it)
- **Use MongoDB Atlas** for better uptime
- **Monitor Groq API** usage on free tier
- **Cache results** if regenerating same SRS

---

## Version Information

- **Python**: 3.10+
- **FastAPI**: 0.100.0+
- **Groq**: Latest
- **MongoDB**: 4.4+
- **Node.js**: 14+ (for Mermaid)

---

Good luck! 🚀 Once startup is complete, read **startup_guide.md** for the full user journey.
