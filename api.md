# 📡 SRS Engine API Documentation

## Overview

This document describes all REST API endpoints in the SRS Engine system. The API is built with **FastAPI** and handles user authentication, SRS generation, and document processing.

## Base URL

```
http://localhost:8000
```

## Authentication

### Session-Based Authentication

The system uses **cookie-based sessions**. After login, a session cookie is automatically set and included in all requests.

**How it works:**
1. User logs in → Server creates session cookie
2. Browser automatically sends cookie with each request
3. Server validates cookie, checks if user is logged in
4. API endpoints check if user is authenticated

**Key Points:**
- ✅ Automatic cookie handling (no manual Bearer tokens)
- ✅ Secure HttpOnly cookies
- ✅ Session expires after inactivity
- ✅ All protected endpoints require valid session

---

## API Endpoints

### ⚠️ Authentication Endpoints

#### 1. Login with Username/Password

**Endpoint:**
```
POST /auth/login
```

**Purpose:** User logs in with username and password

**Request:**
```
Content-Type: application/x-www-form-urlencoded

username=john_doe
password=mypassword123
```

**Response (Redirect):**
```
Status: 302 (Redirect)
Location: /home
```

**Success Behavior:**
- ✅ Session cookie created
- ✅ Redirects to `/home`
- ✅ User logged in

**Failure Response:**
```
Status: 302 (Redirect)
Location: /login?error=Invalid+username+or+password
```

**Frontend Usage:**
```html
<form action="/auth/login" method="POST">
  <input type="text" name="username" required>
  <input type="password" name="password" required>
  <button type="submit">Login</button>
</form>
```

---

#### 2. Register New User

**Endpoint:**
```
POST /auth/register
```

**Purpose:** Create new user account

**Request:**
```
Content-Type: application/x-www-form-urlencoded

username=john_doe
password=mypassword123
email=john@example.com (optional)
```

**Response (Redirect):**
```
Status: 302 (Redirect)
Location: /home
```

**Success Behavior:**
- ✅ New user created in database
- ✅ Session cookie created
- ✅ Redirects to `/home`

**Failure Response:**
```
Status: 302 (Redirect)
Location: /login?error=Username+already+exists
```

**Validation:**
- Username: Must be unique, not empty
- Password: Hashed with bcrypt (never stored plain)
- Email: Optional, can be empty

---

#### 3. Google OAuth Login

**Endpoint:**
```
GET /auth/google/login
```

**Purpose:** Authenticate using Google account

**Flow:**
```
1. User clicks "Login with Google"
   ↓
2. Redirects to Google login page
   ↓
3. User approves access
   ↓
4. Redirects to /auth/google/callback
   ↓
5. System creates/updates user in DB
   ↓
6. Session created, redirects to /home
```

**Frontend Usage:**
```html
<a href="/auth/google/login" class="btn btn-google">Login with Google</a>
```

**Requirements:**
- Google OAuth configured in `.env`
- `GOOGLE_OAUTH_CLIENT_ID` set
- `GOOGLE_OAUTH_CLIENT_SECRET` set
- `GOOGLE_OAUTH_REDIRECT_URI` set

---

#### 4. Logout

**Endpoint:**
```
GET /auth/logout
```

**Purpose:** End user session

**Request:**
```
No body required
(Cookie automatically sent by browser)
```

**Response:**
```
Status: 302 (Redirect)
Location: /login
```

**Success Behavior:**
- ✅ Session cookie cleared
- ✅ Redirects to `/login`
- ✅ User logged out

**Frontend Usage:**
```html
<a href="/auth/logout">Logout</a>
```

---

### 📄 Page Endpoints (HTML Pages)

These serve web pages, not API data.

#### GET /
**Redirects to `/home`**

#### GET /home
**Serves:** SRS Generator home page (requires login)

#### GET /srs-generator
**Serves:** SRS Generator page (requires login)

#### GET /features
**Serves:** Features page (requires login)

#### GET /faqs
**Serves:** FAQ page (requires login)

#### GET /about
**Serves:** About page (requires login)

#### GET /contact
**Serves:** Contact page (requires login)

#### GET /login
**Serves:** Login page (redirects if already logged in)

---

### 🤖 SRS Generation API Endpoints

These endpoints handle AI-powered document generation. **All require user to be logged in.**

---

#### 1. Enhance Problem Statement

**Endpoint:**
```
POST /enhance-problem-statement
```

**Purpose:** Use AI to improve and expand a problem statement

**Request Body:**
```json
{
  "project_name": "Customer Churn Prediction System",
  "problem_statement": "Reduce customer churn by predicting at-risk customers"
}
```

**Request Parameters:**
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `project_name` | string | ✅ Yes | Name of the project |
| `problem_statement` | string | ✅ Yes | Original problem statement (min 30 chars) |

**Response (Success):**
```
Status: 200 OK

{
  "enhanced_problem_statement": "A comprehensive system designed to identify and predict customer churn through advanced machine learning algorithms and predictive analytics. The system will analyze customer behavior patterns, interaction history, and usage trends to identify at-risk customers before they leave. This proactive approach enables the organization to implement targeted retention strategies, improve customer satisfaction, and maximize lifetime customer value."
}
```

**Response (Failure):**
```
Status: 500 Internal Server Error

{
  "detail": "Error in enhance_problem_statement: Invalid API key"
}
```

**What Happens Behind the Scenes:**
1. ✅ Creates unique session ID
2. ✅ Validates input data
3. ✅ Calls Groq API with enhancement prompt
4. ✅ Parses JSON response
5. ✅ Validates enhanced statement (50-1000 chars)
6. ✅ Returns enhanced version

**Frontend Example:**
```javascript
const response = await fetch('/enhance-problem-statement', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    project_name: 'My Project',
    problem_statement: 'Fix user login issues'
  })
});

const result = await response.json();
console.log(result.enhanced_problem_statement);
```

---

#### 2. Auto-Generate Section

**Endpoint:**
```
POST /auto-generate-section
```

**Purpose:** Use AI to automatically generate specific SRS sections (features or user flow)

**Request Body:**
```json
{
  "project_name": "Customer Churn Prediction System",
  "problem_statement": "Reduce customer churn...",
  "section_type": "features"
}
```

**Request Parameters:**
| Field | Type | Required | Allowed Values |
|-------|------|----------|---|
| `project_name` | string | ✅ Yes | Any string |
| `problem_statement` | string | ✅ Yes | Detailed description |
| `section_type` | string | ✅ Yes | `"features"` or `"flow"` |

**Response for section_type="features":**
```
Status: 200 OK

{
  "core_features": [
    "Customer data aggregation and preprocessing",
    "Machine learning model training and evaluation",
    "Real-time churn prediction for active customers",
    "Retention strategy recommendations",
    "Analytics dashboard for monitoring"
  ]
}
```

**Response for section_type="flow":**
```
Status: 200 OK

{
  "primary_user_flow": "Admin logs in → Uploads customer data → System processes and trains model → Dashboard loads with predictions → Admin views at-risk customers → Generates retention reports → Exports for marketing team"
}
```

**Response (Failure):**
```
Status: 500 Internal Server Error

{
  "detail": "Error in auto_generate_section: No API key provided"
}
```

**Processing Time:**
- First generation: 15-30 seconds
- Groq AI processing: 8-20 seconds
- Includes validation and formatting

**Frontend Example:**
```javascript
// Generate features
const response = await fetch('/auto-generate-section', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    project_name: 'E-commerce Platform',
    problem_statement: 'Need robust online marketplace',
    section_type: 'features'
  })
});

const data = await response.json();
// data.core_features is an array of feature strings
```

---

#### 3. Generate Full SRS Document

**Endpoint:**
```
POST /generate_srs
```

**Purpose:** Generate a complete SRS document with all sections and diagrams

**Request Body (Complex):**
```json
{
  "project_identity": {
    "project_name": "Customer Churn Prediction System",
    "author": ["John Doe", "Jane Smith"],
    "organization": "DataCorp Inc",
    "problem_statement": "Reduce customer churn by predicting at-risk customers",
    "target_users": ["Manager", "Analyst"]
  },
  "system_context": {
    "application_type": "Web Application",
    "domain": "Finance & Banking"
  },
  "functional_scope": {
    "core_features": [
      "Customer data aggregation",
      "ML model training",
      "Real-time predictions"
    ],
    "primary_user_flow": "Login → Upload Data → View Dashboard → Generate Reports"
  },
  "non_functional_requirements": {
    "expected_user_scale": "1k-100k",
    "performance_expectation": "High"
  },
  "security_and_compliance": {
    "authentication_required": true,
    "sensitive_data_handling": true,
    "compliance_requirements": ["GDPR", "CCPA"]
  },
  "technical_preferences": {
    "preferred_backend": "Python",
    "database_preference": "PostgreSQL",
    "deployment_preference": "Cloud"
  }
}
```

**Request Structure Breakdown:**

| Section | Purpose |
|---------|---------|
| `project_identity` | Basic project info |
| `system_context` | What type of system, what domain |
| `functional_scope` | Features and user workflows |
| `non_functional_requirements` | Performance, scalability needs |
| `security_and_compliance` | Security and legal requirements |
| `technical_preferences` | Technology preferences |

**Response (Success):**
```
Status: 200 OK

{
  "message": "SRS document generated successfully",
  "project_name": "Customer Churn Prediction System",
  "document_path": "generated_srs/Customer_Churn_Prediction_System_SRS.docx",
  "diagrams": {
    "user_interfaces": "generated_images/Customer_Churn_Prediction_System_user_interfaces_diagram.mmd",
    "software_interfaces": "generated_images/Customer_Churn_Prediction_System_software_interfaces_diagram.mmd",
    "hardware_interfaces": "generated_images/Customer_Churn_Prediction_System_hardware_interfaces_diagram.mmd",
    "communication_interfaces": "generated_images/Customer_Churn_Prediction_System_communication_interfaces_diagram.mmd"
  }
}
```

**Response (Failure):**
```
Status: 500 Internal Server Error

{
  "detail": "Error generating SRS: Invalid input data"
}
```

**Processing Flow:**
```
1. Validate all input with Pydantic schemas
2. Create session with unique ID
3. Run 7 AI agents in parallel (15-20 seconds):
   - Introduction agent
   - Overall description agent
   - System features agent
   - External interfaces agent
   - NFR (Non-Functional Requirements) agent
   - Glossary agent
   - Assumptions agent
4. Wait 20 seconds for results
5. Merge all responses
6. Generate Mermaid diagrams
7. Create .docx file with python-docx
8. Save to generated_srs/ directory
9. Return paths to client
```

**Total Processing Time:**
- Validation: 1-2 seconds
- AI generation: 60-90 seconds
- Diagram rendering: 15-20 seconds
- Document creation: 5-10 seconds
- **Total: 90-120 seconds (1.5-2 minutes)**

**Frontend Example:**
```javascript
const srsData = {
  project_identity: {
    project_name: 'E-commerce Platform',
    author: ['Alice', 'Bob'],
    organization: 'ShopCorp',
    problem_statement: 'Need online marketplace',
    target_users: ['Admin', 'Customer']
  },
  // ... other sections ...
};

const response = await fetch('/generate_srs', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(srsData)
});

const result = await response.json();
console.log('Downloaded:', result.document_path);
```

---

## Error Handling

### Standard Error Response Format

```json
{
  "detail": "Human-readable error message explaining what went wrong"
}
```

### Common HTTP Status Codes

| Status | Meaning | Example |
|--------|---------|---------|
| **200** | Success | SRS generated successfully |
| **302** | Redirect | Login successful, redirect to home |
| **400** | Bad Request | Invalid JSON in request body |
| **401** | Unauthorized | User not logged in (session expired) |
| **500** | Server Error | Groq API failed, database error |

### Common Error Causes

| Error | Cause | Fix |
|-------|-------|-----|
| "No API key provided" | `GROQ_API_KEY` not in `.env` | Add API key to `.env` |
| "Invalid username or password" | Wrong credentials | Check login details |
| "Username already exists" | Sign up with existing user | Use different username |
| "Database connection failed" | MongoDB offline | Start MongoDB or check URI |
| "Mermaid CLI not found" | Diagram generation failed | Re-install mermaid-cli |
| "Session expired" | Cookie expired or cleared | Log in again |

---

## Data Validation Rules

### Project Identity
```
project_name: 1-200 characters, required
author: Array of 1+ names, required
organization: 1-200 characters, required
problem_statement: 10-2000 characters, required
target_users: Array of 1+ users, required
```

### System Context
```
application_type: Web/Mobile/Desktop/API, required
domain: Industry/category, required
```

### Functional Scope
```
core_features: Array of 1+ features, required
primary_user_flow: 0-1000 characters, optional
```

### Non-Functional Requirements
```
expected_user_scale: <100, 100-1k, 1k-100k, >100k, required
performance_expectation: Normal, High, Real-time, required
```

### Security and Compliance
```
authentication_required: true/false, required
sensitive_data_handling: true/false, required
compliance_requirements: Array of 0+ items, optional
```

### Technical Preferences
```
preferred_backend: String, optional
database_preference: String, optional
deployment_preference: String, optional
```

---

## Rate Limiting & Quotas

### Groq Free Tier
- **Requests per minute**: 30 RPM
- **Tokens per day**: 14,400 tokens/day
- **Cost**: Free
- **No credit card required**

### Implications for SRS Engine
- ✅ Can generate ~8-10 SRS documents per day (free tier)
- ⚠️ Each `/auto-generate-section` uses ~1,000-1,500 tokens
- ⚠️ Full SRS generation uses ~8,000-12,000 tokens
- ⚠️ If you exceed limit, API returns error

### Monitoring Usage
1. Check [console.groq.com](https://console.groq.com)
2. View "API Usage" dashboard
3. See tokens used today
4. Plan accordingly

---

## Request/Response Examples

### Example 1: Complete User Journey

**1. User visits site**
```
GET /login
Response: Login HTML page
```

**2. User logs in**
```
POST /auth/login
Body: username=john&password=pass123
Response: Redirect to /home
```

**3. User views generator**
```
GET /srs-generator
Response: HTML form (requires logged-in session)
```

**4. User fills form and enhances problem statement**
```
POST /enhance-problem-statement
Body: {
  "project_name": "Smart Library",
  "problem_statement": "Manage book inventory"
}
Response: {
  "enhanced_problem_statement": "A comprehensive library management system..."
}
```

**5. User generates full SRS**
```
POST /generate_srs
Body: { complete SRS data }
Response: {
  "message": "SRS document generated successfully",
  "document_path": "generated_srs/Smart_Library_SRS.docx",
  "diagrams": { ... }
}
```

**6. User downloads document**
```
File downloaded from server
Location: generated_srs/Smart_Library_SRS.docx
```

**7. User logs out**
```
GET /auth/logout
Response: Redirect to /login
```

---

## CORS & Security Headers

### Allowed Methods
- GET (Page requests)
- POST (Form submissions, API calls)

### Allowed Headers
- Content-Type
- Accept

### Security Features
- ✅ Session-based auth (no APIs keys in client)
- ✅ HttpOnly cookies (protect from JavaScript access)
- ✅ CSRF protection
- ✅ Password hashing with bcrypt
- ✅ MongoDB connection encrypted (if using Atlas)

---

## Performance Characteristics

### Response Times

| Endpoint | Time | Depends On |
|----------|------|-----------|
| `/auth/login` | 200-500ms | Database query |
| `/enhance-problem-statement` | 10-20s | Groq API response |
| `/auto-generate-section` | 12-25s | Groq API response |
| `/generate_srs` | 90-120s | 7 AI agents + rendering |

### Network Requirements
- **Minimum**: 2 Mbps download
- **Recommended**: 10+ Mbps
- **Latency matters** more than bandwidth
- Groq servers hosted globally (fast)

---

## API Client Examples

### cURL
```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -d "username=john&password=pass123" \
  -c cookies.txt

# Enhance statement
curl -X POST http://localhost:8000/enhance-problem-statement \
  -H "Content-Type: application/json" \
  -b cookies.txt \
  -d '{
    "project_name": "My Project",
    "problem_statement": "Fix bugs"
  }'
```

### Python Requests
```python
import requests

session = requests.Session()

# Login
response = session.post('http://localhost:8000/auth/login', 
  data={'username': 'john', 'password': 'pass123'})

# Enhance
result = session.post(
  'http://localhost:8000/enhance-problem-statement',
  json={
    'project_name': 'My Project',
    'problem_statement': 'Fix bugs'
  }
)
print(result.json())
```

### JavaScript/Fetch
```javascript
// Login (if using form, cookie handled automatically)
// For API requests, just fetch normally

const response = await fetch('/enhance-problem-statement', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    project_name: 'My Project',
    problem_statement: 'Fix bugs'
  })
});
// Cookie automatically sent and received by browser
```

---

## Websockets & Real-time Features

Currently, SRS Engine uses **HTTP polling**, not WebSockets.

### For Long-Running Operations:
- `/generate_srs` takes 60-120 seconds
- Frontend shows loading spinner
- User waits for response
- No polling or status checking needed

### Future Enhancement:
Could add WebSocket for:
- Real-time progress updates
- Streaming document generation
- Live agent status

---

## API Stability & Versioning

### Current Version
- **No explicit versioning** yet
- All endpoints at `/` root

### Future Versioning (Planned)
- Could use `/api/v1/`, `/api/v2/`, etc.
- Would maintain backward compatibility

### API Guarantee
- ✅ No breaking changes in minor updates
- ✅ Deprecated endpoints stay for 2+ versions
- ✅ New endpoints added in minor versions
- ⚠️ Major versions may have breaking changes

---

## Troubleshooting API Issues

### Issue: 401 Unauthorized
**Cause**: Not logged in or session expired
```bash
# Solution: Login again
POST /auth/login
```

### Issue: 500 Internal Server Error
**Cause**: Groq API failure or database error
```bash
# Check:
1. Is GROQ_API_KEY correct?
2. Is MongoDB running?
3. Check server logs
LOG_LEVEL=DEBUG uvicorn srs_engine.main:app --reload
```

### Issue: Timeout (request takes > 180s)
**Cause**: Network slow or server overloaded
```
# Solutions:
1. Check internet speed
2. Try request again
3. Check Groq API status
```

### Issue: CORS Error in Browser
**Cause**: Browser blocking cross-origin request
```
Likely means frontend on different origin than backend
Make sure both use same http://localhost:8000
```

---

## API Limits & Quotas Summary

| Limit | Value | Resets |
|-------|-------|--------|
| **Groq Requests/Min** | 30 | Every minute |
| **Groq Tokens/Day** | 14,400 | Midnight UTC |
| **Session Timeout** | 24 hours | Last activity +24h |
| **File Size** | Unlimited | - |
| **Users** | Unlimited | - |

---

Good luck building with the SRS Engine API! 🚀
