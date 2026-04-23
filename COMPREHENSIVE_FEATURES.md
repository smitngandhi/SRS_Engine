# 🚀 SRS Engine - Comprehensive Features & API Documentation

**Version:** 1.0  
**Last Updated:** April 2026  
**Purpose:** Complete feature overview and API reference for all stakeholders

---

## 📋 Table of Contents

1. [Project Overview](#project-overview)
2. [Core Features](#core-features)
3. [Authentication System](#authentication-system)
4. [API Endpoints](#api-endpoints)
5. [Domain-Specific Support](#domain-specific-support)
6. [User Workflows](#user-workflows)
7. [Technical Architecture](#technical-architecture)

---

## 📌 Project Overview

**SRS Engine** is a production-grade, AI-powered platform for generating IEEE 830-compliant Software Requirements Specification (SRS) documents. It uses multi-agent AI architecture with async job processing, real-time tracking, and automatic email delivery.

### Key Technologies
- **Backend:** FastAPI (Python 3.11+)
- **Database:** MongoDB
- **Job Queue:** RabbitMQ
- **AI:** Groq API, LiteLLM (for multi-LLM support)
- **Document Format:** .docx, .pdf (planned)
- **Diagrams:** Mermaid → PNG rendering
- **Authentication:** Session-based + Google OAuth

---

## ✨ Core Features

### 1. 🤖 Multi-Agent SRS Generation

**What it does:** AI-powered 7-step guided form generates IEEE 830-compliant SRS documents

**Process:**
- **Step 1:** Project Identity (name, description, stakeholders)
- **Step 2:** System Context (scope, users, environment)
- **Step 3:** Functional Scope (features, capabilities)
- **Step 4:** Non-Functional Requirements (performance, security, scalability)
- **Step 5:** Security Considerations (authentication, encryption, compliance)
- **Step 6:** Technical Architecture (technologies, integrations)
- **Step 7:** Output Control (detail level, format selection)

**Output Quality Levels:**
- 🟢 **High-Level:** Executive summary (5-10 pages)
- 🟡 **Technical:** Detailed specifications (15-25 pages)  
- 🔴 **Enterprise:** Comprehensive with diagrams (30-50 pages)

---

### 2. 📄 Problem Statement Enhancement

**Feature:** AI automatically improves and expands problem statements

**Input:** Initial problem statement (minimum 30 characters)

**Output:** Enhanced, detailed problem statement (50-1,000 characters)

**Use Case:** Users can quickly turn rough ideas into polished problem descriptions

---

### 3. 🎯 Auto-Generate Section

**Feature:** Generate specific sections on-demand using contextual data

**Supported Sections:**
- System Overview
- Functional Requirements
- Non-Functional Requirements
- Interface Specifications
- Security Architecture
- Implementation Constraints

**Benefits:** Refine specific sections without regenerating entire document

---

### 4. 📊 Architecture Diagram Generation

**Feature:** Automatic generation of 4 system architecture diagrams

**Diagrams Generated:**
1. **User Interface Diagram** - User interactions and touchpoints
2. **Hardware Architecture Diagram** - System hardware components
3. **Software Architecture Diagram** - System components and layers
4. **Communication Interfaces Diagram** - External integrations and APIs

**Output Format:** Mermaid diagrams → PNG (embedded in final document)

**Intelligence:** AI-powered diagram generation based on SRS content

---

### 5. 📁 Document Upload & Parsing

**Feature:** Upload existing SRS documents (PDF/DOCX) and parse to structured format

**Supported Formats:**
- ✅ DOCX (Microsoft Word)
- ✅ PDF (Adobe PDF)

**Parser Output:**
- Unified JSON document structure
- Section-by-section extraction
- Metadata preservation
- OCR-ready (for image-heavy PDFs)

**Use Case:** Migrate legacy SRS documents into the platform

---

### 6. 🔄 SRS Upgrader (Section-by-Section Enhancement)

**Feature:** AI-assisted workflow to identify and improve weak sections

**Workflow:**
1. **Upload** existing SRS document
2. **Analyze** - AI scores each section (0-10)
3. **Flag** sections below threshold (default: 6.5)
4. **Question** - AI generates improvement questions
5. **Answer** - User provides answers
6. **Enhance** - AI rewrites sections with new context
7. **Export** - Download upgraded document

**Quality Metrics:** Detailed scoring + recommendation engine

---

### 7. 💬 Intelligent Chatbot (Q&A System)

**Feature:** Ask questions about generated SRS documents

**Capabilities:**
- **Tool-Calling Loop** - LLM intelligently fetches relevant sections
- **RAG Fallback** - Semantic search when tool-calling fails
- **Context-Aware** - Understands document structure and relationships
- **Multi-Turn** - Maintains conversation context across questions

**Example Questions:**
- "What are the security requirements?"
- "How does user authentication work?"
- "What are the performance targets?"
- "List all external integrations"

---

### 8. 📋 Job Tracker Dashboard

**Feature:** Real-time monitoring of SRS generation jobs

**Features:**
- ✅ Job status filters (All, Pending, Processing, Completed, Failed)
- ✅ Progress bars per job
- ✅ Completion time tracking
- ✅ One-click download of generated documents
- ✅ Server-Sent Events (SSE) for live updates

**Statuses:**
- 🔵 **Pending** - Waiting in queue
- 🟡 **Processing** - Currently running
- 🟢 **Completed** - Ready to download
- 🔴 **Failed** - Requires user action

---

### 9. 📧 Email Delivery

**Feature:** Automatic email notification + document attachment

**Triggered:** When SRS generation completes successfully

**Contents:**
- Status notification
- Generated SRS document (.docx attachment)
- Download link (alternative)
- Timestamp and metadata

**Configuration:** SMTP settings in `.env`

---

### 10. 🗄️ Workspace & Document History

**Feature:** Persistent storage of all generated documents

**Views:**
- **My Generated SRS** - List all documents with:
  - Project name
  - Generation date
  - File size
  - Direct download link
  - Delete option

**Benefits:** No re-generation needed for past projects

---

### 11. 🔐 Authentication & Authorization

**Feature:** Secure user management with multiple auth methods

**Methods:**
1. **Username/Password**
   - Bcrypt password hashing
   - Unique username requirement
   - Optional email field

2. **Google OAuth**
   - Single sign-on
   - Auto user-creation on first login
   - Session-based persistence

**Session Management:**
- HttpOnly cookies (cannot be accessed by JavaScript)
- Server-side session validation
- Automatic expiry on inactivity
- CSRF protection enabled

---

### 12. 📞 Contact & Support

**Feature:** User-to-admin communication channel

**Form Fields:**
- Name (required)
- Email (required, validated)
- Subject (required)
- Message (required, 10-5000 chars)

**Spam Protection:** Honeypot field for bot detection

**Delivery:** Email forwarded to support inbox

---

### 13. 📱 Responsive Web Interface

**Feature:** Full-featured web UI for all operations

**Pages:**
- 🏠 **Home** - Project dashboard
- 🤖 **SRS Generator** - 7-step form
- 📊 **Job Tracker** - Real-time status
- 📁 **Workspace** - Document history
- 💬 **Chatbot** - Q&A interface
- 🔧 **Upgrader** - Section enhancement
- ❓ **FAQs** - Help and documentation
- 📖 **About** - Project information
- 📞 **Contact** - Support form

---

## 🔐 Authentication System

### How Authentication Works

```
User Action                 System Response
════════════════════════════════════════════════════
1. Visit /login         →  Serve login page
2. Enter credentials    →  Validate username/password
3. Credentials valid    →  Create session, set cookie
4. Make request         →  Browser sends cookie
5. Server validates     →  Check session is active
6. Session active       →  Allow access to endpoint
7. Session expired      →  Redirect to /login
```

### Protected Resources

All API endpoints except these **require authentication:**
- `GET /` (redirects to home)
- `GET /login`
- `GET /about` (public info)
- `GET /features` (public info)
- `GET /faqs` (public info)
- `POST /auth/login`
- `POST /auth/register`
- `GET /auth/google/login`
- `POST /api/contact`

---

## 🔌 API Endpoints

### Authentication APIs

#### 1. Register User
```
POST /auth/register

Request:
{
  "username": "john_doe",
  "password": "secure_password",
  "email": "john@example.com"  (optional)
}

Response (Success):
Status: 302
Location: /home

Response (Failure):
Status: 302
Location: /login?error=Username+already+exists
```

---

#### 2. Login
```
POST /auth/login

Request:
{
  "username": "john_doe",
  "password": "secure_password"
}

Response (Success):
Status: 302
Location: /home
Cookie: session=<session_id>

Response (Failure):
Status: 302
Location: /login?error=Invalid+credentials
```

---

#### 3. Google OAuth Login
```
GET /auth/google/login

Flow:
1. User clicks link
2. Redirects to Google signin
3. Google redirects to callback with auth code
4. System creates/updates user
5. Session created
6. Redirects to /home
```

---

#### 4. Logout
```
GET /auth/logout

Response:
Status: 302
Location: /login
Cookie: session=<cleared>
```

---

### SRS Generation APIs

#### 1. Enhance Problem Statement
```
POST /enhance-problem-statement

Request:
{
  "project_name": "E-Commerce Platform",
  "problem_statement": "Build a scalable online store"
}

Response (Success):
{
  "enhanced_problem_statement": "A comprehensive e-commerce platform designed to provide seamless online shopping experiences..."
}

Response (Failure):
{
  "detail": "Error in enhance_problem_statement: <error_message>"
}
```

---

#### 2. Auto-Generate Section
```
POST /auto-generate-section

Request:
{
  "project_name": "E-Commerce Platform",
  "section_type": "functional_requirements",
  "context": "Online store with inventory management..."
}

Response:
{
  "generated_content": "<detailed section content>"
}
```

---

#### 3. Generate Full SRS (Async)
```
POST /generate_srs

Request:
{
  "project_name": "E-Commerce Platform",
  "problem_statement": "...",
  "system_context": "...",
  "functional_scope": [...],
  "non_functional_requirements": {...},
  "security_considerations": {...},
  "technical_architecture": {...},
  "detail_level": "technical",
  "include_diagrams": true
}

Response (Immediate):
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000"
}

Note: Document generation happens asynchronously in background
```

---

#### 4. Get Job Status
```
GET /job/{job_id}/status

Response:
{
  "job_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 65,
  "created_at": "2026-04-16T10:00:00Z",
  "updated_at": "2026-04-16T10:05:00Z"
}
```

---

#### 5. Stream Job Status (Server-Sent Events)
```
GET /job/{job_id}/status/stream

Response: EventStream
data: {"status": "processing", "progress": 25, "message": "Generating architecture diagrams..."}
data: {"status": "processing", "progress": 50, "message": "Writing functional requirements..."}
data: {"status": "completed", "progress": 100, "document_id": "..."}

Benefits:
- Real-time updates in browser
- Automatic connection close on completion
- No polling required
```

---

#### 6. Download Generated Document
```
GET /job/{job_id}/download

Response:
Status: 200
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="ProjectName_SRS.docx"
<binary .docx content>
```

---

### Document Upload & Parse APIs

#### 1. Upload SRS Document
```
POST /upload/srs

Request:
Content-Type: multipart/form-data
file: <PDF or DOCX file>

Response:
{
  "success": true,
  "file": {
    "file_id": "67890abcd",
    "original_filename": "existing_srs.docx",
    "file_type": "docx",
    "file_size": 125000,
    "storage_path": "user_uploads/123/67890abcd.docx",
    "uploaded_at": "2026-04-16T10:00:00Z"
  }
}
```

---

#### 2. List Uploaded Files
```
GET /upload/srs/list

Response:
{
  "files": [
    {
      "file_id": "67890abcd",
      "original_filename": "existing_srs.docx",
      "file_type": "docx",
      "file_size": 125000,
      "uploaded_at": "2026-04-16T10:00:00Z"
    }
  ]
}
```

---

#### 3. Delete Uploaded File
```
DELETE /upload/srs/{file_id}

Response:
{
  "success": true,
  "deleted_file_id": "67890abcd"
}
```

---

#### 4. Parse Uploaded File
```
POST /parse/srs/{file_id}

Response:
{
  "success": true,
  "file_id": "67890abcd",
  "parsed_at": "2026-04-16T10:05:00Z",
  "sections_extracted": 15,
  "parsed_document_path": "parsed_docs/123/parsed_67890abcd.json"
}
```

---

#### 5. Get Parsed Document
```
GET /parse/srs/{file_id}

Response:
{
  "file_id": "67890abcd",
  "original_filename": "existing_srs.docx",
  "sections": {
    "introduction": {...},
    "overall_description": {...},
    "system_features": [...],
    "external_interfaces": {...},
    "nfr": {...},
    "glossary": [...]
  }
}
```

---

#### 6. Get Parse Preview
```
GET /parse/srs/{file_id}/preview

Response:
{
  "file_id": "67890abcd",
  "section_titles": [
    "1. Introduction",
    "2. Overall Description",
    "3. System Features",
    "4. External Interfaces",
    "5. Non-Functional Requirements",
    "6. Glossary"
  ],
  "total_sections": 6
}
```

---

### SRS Upgrade/Enhancement APIs

#### 1. Create Upgrade Session
```
POST /upgrade/srs/{file_id}/session

Response:
{
  "session_id": "session-12345",
  "file_id": "67890abcd",
  "sections_snapshot": [
    {
      "section_id": "intro-001",
      "title": "Introduction",
      "content": "..."
    }
  ],
  "status": "initialized"
}
```

---

#### 2. Analyze Sections
```
POST /upgrade/srs/{file_id}/analyse

Request:
{
  "score_threshold": 6.5
}

Response (as EventStream):
data: {"event": "analysis_started"}
data: {"event": "section_analyzed", "section_id": "intro-001", "score": 8.2, "status": "good"}
data: {"event": "section_analyzed", "section_id": "func-001", "score": 5.1, "status": "flagged"}
data: {"event": "analysis_completed", "flagged_count": 3}
```

---

#### 3. Generate Questions
```
POST /upgrade/srs/{file_id}/questions

Response:
{
  "questions": [
    {
      "section_id": "func-001",
      "section_title": "Functional Requirements",
      "question": "What are the specific user roles?",
      "current_content": "..."
    }
  ]
}
```

---

#### 4. Submit Answers
```
POST /upgrade/srs/{file_id}/answers

Request:
{
  "submissions": [
    {
      "section_id": "func-001",
      "question_id": "q-001",
      "answer": "Admin, User, Guest roles with specific permissions"
    }
  ]
}

Response:
{
  "success": true,
  "sections_enhanced": 3
}
```

---

#### 5. Update Section Status
```
PATCH /upgrade/srs/{file_id}/section/{section_id}

Request:
{
  "action": "accept",  
  "edited_content": ""  (optional, for "edit" action)
}

Response:
{
  "success": true,
  "section_id": "func-001",
  "action": "accept",
  "updated_at": "2026-04-16T10:10:00Z"
}
```

---

#### 6. Get Upgrade Session State
```
GET /upgrade/srs/{file_id}/session

Response:
{
  "session_id": "session-12345",
  "file_id": "67890abcd",
  "current_step": "questions",
  "sections": [
    {
      "section_id": "intro-001",
      "title": "Introduction",
      "original_content": "...",
      "enhanced_content": "...",
      "action_status": "pending"
    }
  ]
}
```

---

#### 7. Export Enhanced Document
```
GET /upgrade/srs/{file_id}/export

Response:
Status: 200
Content-Type: application/vnd.openxmlformats-officedocument.wordprocessingml.document
Content-Disposition: attachment; filename="ProjectName_SRS_Enhanced.docx"
<binary .docx content>
```

---

### Diagram Generation APIs

#### 1. Create Diagram
```
POST /diagram/create

Request:
{
  "project_name": "E-Commerce Platform",
  "diagram_type": "user_interface",
  "context": "Online shopping with user profiles...",
  "detail_level": "technical"
}

Response:
{
  "diagram_id": "diag-12345",
  "diagram_type": "user_interface",
  "mermaid_code": "graph TD\n  User-->Cart\n  Cart-->Checkout",
  "png_url": "/diagrams/diag-12345.png"
}
```

---

#### 2. List Diagrams by Project
```
GET /diagram/project/{project_name}

Response:
{
  "project_name": "E-Commerce Platform",
  "diagrams": [
    {
      "diagram_id": "diag-12345",
      "diagram_type": "user_interface",
      "created_at": "2026-04-16T10:00:00Z"
    },
    {
      "diagram_id": "diag-12346",
      "diagram_type": "software_architecture",
      "created_at": "2026-04-16T10:05:00Z"
    }
  ]
}
```

---

#### 3. Get Diagram Details
```
GET /diagram/{diagram_id}

Response:
{
  "diagram_id": "diag-12345",
  "project_name": "E-Commerce Platform",
  "diagram_type": "user_interface",
  "mermaid_code": "...",
  "png_url": "/diagrams/diag-12345.png",
  "created_at": "2026-04-16T10:00:00Z",
  "last_modified": "2026-04-16T10:00:00Z"
}
```

---

#### 4. Regenerate Diagram
```
POST /diagram/{diagram_id}/regenerate

Request:
{
  "updated_context": "New context information..."
}

Response:
{
  "success": true,
  "diagram_id": "diag-12345",
  "mermaid_code": "...",
  "png_url": "/diagrams/diag-12345.png"
}
```

---

#### 5. Edit Diagram
```
POST /diagram/{diagram_id}/edit

Request:
{
  "mermaid_code": "graph TD\n  A-->B"
}

Response:
{
  "success": true,
  "diagram_id": "diag-12345",
  "mermaid_code": "...",
  "png_url": "/diagrams/diag-12345.png"
}
```

---

#### 6. Delete Diagram
```
DELETE /diagram/{diagram_id}

Response:
{
  "success": true,
  "deleted_diagram_id": "diag-12345"
}
```

---

### Chatbot APIs

#### 1. List Chat Documents
```
GET /api/chat/documents

Response:
{
  "documents": [
    {
      "doc_id": "ecommerce_platform",
      "project_name": "E-Commerce Platform",
      "created_at": "2026-04-16T10:00:00Z"
    }
  ]
}
```

---

#### 2. Get Document Index (Table of Contents)
```
GET /api/chat/documents/{doc_id}/index

Response:
{
  "doc_id": "ecommerce_platform",
  "toc": [
    {
      "section_id": "introduction",
      "title": "Introduction",
      "subsections": [
        {"id": "intro_purpose", "title": "Purpose"},
        {"id": "intro_scope", "title": "Scope"}
      ]
    },
    {
      "section_id": "features",
      "title": "System Features",
      "subsections": [...]
    }
  ]
}
```

---

#### 3. Chat Query (Ask Questions)
```
POST /api/chat/query

Request:
{
  "doc_id": "ecommerce_platform",
  "query": "What are the security requirements?",
  "conversation_history": [
    {"role": "user", "content": "..."},
    {"role": "assistant", "content": "..."}
  ]
}

Response:
{
  "response": "The security requirements include...",
  "sources": [
    {
      "section_id": "nfr_section",
      "section_title": "Non-Functional Requirements",
      "confidence": 0.92
    }
  ],
  "can_continue": true
}
```

---

### Support/Contact APIs

#### 1. Submit Contact Form
```
POST /api/contact

Request:
{
  "name": "John Doe",
  "email": "john@example.com",
  "subject": "Feature Request",
  "message": "Can you add support for PDF export?"
}

Response:
{
  "ok": true
}
```

---

## 🌍 Domain-Specific Support

The SRS Engine includes pre-built schemas for **9 industry verticals**, enabling domain-specialized document generation:

### 1. 🚀 Aerospace
**Use Case:** Aircraft systems, avionics, safety-critical systems
- DO-178C compliance focus
- Safety requirement emphasis
- Hardware integration details

### 2. 🚗 Automotive  
**Use Case:** Vehicle systems, embedded systems
- ASPICE compliance
- ISO 26262 (functional safety)
- OTA (Over-The-Air) updates
- ADAS (Advanced Driver Assistance)

### 3. 🛒 E-Commerce
**Use Case:** Online platforms, shopping systems
- Payment processing
- Inventory management
- Multi-tenant support
- Security/PCI compliance

### 4. 📚 Education
**Use Case:** Learning management systems, student portals
- User roles (student, teacher, admin)
- Grading systems
- Course management
- FERPA compliance

### 5. ⚡ Energy
**Use Case:** Power systems, grid management
- Smart grid requirements
- Renewable energy integration
- Load forecasting
- IEC 61131-3 compliance

### 6. 💰 Finance
**Use Case:** Banking, fintech, payment systems
- Regulatory compliance (PCI-DSS, SOX)
- Transaction processing
- Risk management
- Audit trails

### 7. 🏥 Healthcare & Medical Devices
**Use Case:** Hospital systems, medical devices, telemedicine
- HIPAA compliance
- FDA validation (21 CFR Part 11)
- Patient data security
- Clinical workflows

### 8. 📡 Telecom
**Use Case:** Telecom infrastructure, IoT platforms
- Network protocols
- 5G/6G readiness
- IoT device management
- redundancy/failover

### 9. 🔧 Technical (General)
**Use Case:** Generic software systems
- Standard IEEE 830-1998 format
- Flexible for any industry
- Quick start template

---

## 👥 User Workflows

### Workflow 1: First-Time SRS Generation

```
1. User registers account
   └─> Visit /login
   └─> Click "Register"
   └─> Enter username, password, (optional) email

2. Login
   └─> Navigate to /srs-generator
   └─> See 7-step form

3. Fill out 7-step form
   ├─ Step 1: Project Identity
   ├─ Step 2: System Context
   ├─ Step 3: Functional Scope
   ├─ Step 4: Non-Functional Requirements
   ├─ Step 5: Security Considerations
   ├─ Step 6: Technical Architecture
   └─ Step 7: Output Control (detail level + diagrams)

4. Submit for generation
   └─> POST /generate_srs
   └─> Get job_id immediately
   └─> Redirected to /job-tracker

5. Monitor progress
   └─> Real-time SSE stream of updates
   └─> See progress bar, current step
   └─> Auto-refresh when complete

6. Download document
   └─> Click "Download"
   └─> GET /job/{job_id}/download
   └─> Receive .docx file

7. Document sent via email
   └─> Email arrives with attachment
   └─> Contains generated SRS
```

---

### Workflow 2: Upgrade Existing SRS

```
1. User has existing SRS (PDF/DOCX)
   └─> Navigate to /upgrader
   └─> Click "Upload"

2. Upload document
   └─> POST /upload/srs
   └─> File saved

3. Parse document
   └─> POST /parse/srs/{file_id}
   └─> Sections extracted

4. Create upgrade session
   └─> POST /upgrade/srs/{file_id}/session
   └─> Baseline snapshot created

5. Analyze sections
   └─> POST /upgrade/srs/{file_id}/analyse
   └─> Scores each section
   └─> Flags weak sections

6. Answer improvement questions
   └─> Chatbot asks: "What are the security requirements?"
   └─> User provides detailed answer
   └─> POST /upgrade/srs/{file_id}/answers

7. Review enhancements
   └─> AI rewrites flagged sections
   └─> User can accept/reject/edit
   └─> PATCH /upgrade/srs/{file_id}/section/{section_id}

8. Export upgraded document
   └─> GET /upgrade/srs/{file_id}/export
   └─> Download enhanced .docx
```

---

### Workflow 3: Ask Questions About SRS

```
1. User has generated SRS document
   └─> Navigate to /chatbot
   └─> See list of past projects

2. Select document
   └─> Click project name
   └─> GET /api/chat/documents/{doc_id}/index
   └─> See table of contents

3. Ask question
   └─> Type: "What are the authentication mechanisms?"
   └─> POST /api/chat/query

4. Get AI-powered answer
   └─> LLM tool-calls relevant sections
   └─> Synthesizes answer from content
   └─> Returns with source references

5. Continue conversation
   └─> Ask follow-up: "What about API security?"
   └─> Bot maintains context
   └─> Provides contextual answer
```

---

## 🏗️ Technical Architecture

### System Components

```
┌─────────────────────────────────────────────────────────────────┐
│                        Browser (Frontend)                        │
│                    Jinja2 Templates + JavaScript                 │
└────────────────────────────┬────────────────────────────────────┘
                             │ HTTP/HTTPS
                             ▼
┌─────────────────────────────────────────────────────────────────┐
│                      FastAPI Application                         │
│  ├─ /auth ──────── Authentication Router                         │
│  ├─ /srs ────────── SRS Generation Router                        │
│  ├─ /upload ──────── Document Upload Router                      │
│  ├─ /parse ───────── Document Parser Router                      │
│  ├─ /upgrade ──────── SRS Upgrader Router                        │
│  ├─ /diagram ──────── Diagram Generation Router                  │
│  ├─ /api/chat ──────── Chatbot Router                            │
│  └─ /api/contact ─────── Support Contact Router                  │
└───────────┬──────────────────────────────────────┬───────────────┘
            │ Query/Write                          │ Publish
            ▼                                       ▼
  ┌──────────────────┐                   ┌──────────────────┐
  │    MongoDB       │                   │    RabbitMQ      │
  │   (Database)     │                   │   (Job Queue)    │
  └──────────────────┘                   └────────┬─────────┘
                                                  │ Consume
                                                  ▼
                                        ┌──────────────────┐
                                        │ Worker Process   │
                                        │ (worker.py)      │
                                        │ - SRS generation │
                                        │ - PDF rendering  │
                                        │ - Email delivery │
                                        └──────────────────┘

External Services:
  - Groq API (LLM for content generation)
  - LiteLLM (multi-LLM gateway)
  - Google OAuth (authentication)
  - SMTP (email delivery)
  - Mermaid (diagram generation)
```

---

### Data Flow Diagram

```
SRS Generation Flow:
═══════════════════

Frontend Form
    │
    ├─ Project Identity
    ├─ System Context
    ├─ Functional Scope
    ├─ NFRs
    ├─ Security
    ├─ Technical Architecture
    └─ Output Control
    │
    ▼
POST /generate_srs
    │
    ▼
[Job Created in MongoDB]
    │
    ├─ Status: "pending"
    ├─ User ID linked
    ├─ Timestamp recorded
    └─ Job ID returned to user
    │
    ▼
[Publish to RabbitMQ]
    │
    ▼
[Worker Process Consumes]
    │
    ├─ Validate inputs
    ├─ Initialize 7 AI agents
    ├─ Run agents in parallel:
    │   ├─ Functional Requirements Agent
    │   ├─ NFR Agent
    │   ├─ Security Agent
    │   ├─ Architecture Agent
    │   ├─ Interface Agent
    │   ├─ Glossary Agent
    │   └─ Assumptions Agent
    │
    ├─ Combine agent outputs
    ├─ Generate diagrams (Mermaid → PNG)
    ├─ Create .docx document
    ├─ Update MongoDB: Status = "completed", Document attached
    ├─ Send email to user
    └─ Update Job Status in DB: "completed"
    │
    ▼
[Frontend Polls or SSE Stream]
    │
    ├─ Detects: Status = "completed"
    └─ Shows: Download button active
    │
    ▼ (User clicks Download)
GET /job/{job_id}/download
    │
    ▼
Return .docx file to browser
```

---

### Database Schema Overview

```
Collections:
═════════════

1. users
   - _id: ObjectId
   - username: str (unique)
   - password_hash: str (bcrypt)
   - email: str (optional)
   - google_id: str (optional)
   - created_at: datetime
   - last_login: datetime

2. srs_jobs
   - _id: ObjectId
   - user_id: ObjectId → users._id
   - project_name: str
   - job_status: str (pending|processing|completed|failed)
   - progress: int (0-100)
   - input_data: dict
   - output_document: binary (.docx)
   - document_metadata: dict
   - created_at: datetime
   - completed_at: datetime
   - email_sent: bool

3. uploads
   - _id: ObjectId
   - user_id: ObjectId → users._id
   - file_id: str (unique)
   - original_filename: str
   - file_type: str (pdf|docx)
   - storage_path: str
   - file_size: int
   - uploaded_at: datetime

4. parsed_documents
   - _id: ObjectId
   - user_id: ObjectId → users._id
   - file_id: str → uploads.file_id
   - sections: dict (JSON structure)
   - parsed_at: datetime

5. upgrade_sessions
   - _id: ObjectId
   - user_id: ObjectId → users._id
   - file_id: str → uploads.file_id
   - sections_snapshot: list
   - analysis_results: dict
   - questions: list
   - answers: list
   - enhancements: dict
   - status: str (initialized|analyzed|answered|completed)
   - created_at: datetime

6. diagrams
   - _id: ObjectId
   - user_id: ObjectId → users._id
   - project_name: str
   - diagram_type: str
   - mermaid_code: str
   - png_url: str
   - created_at: datetime
   - modified_at: datetime
```

---

## 🎓 Quick Reference

### For End Users
- **Getting Started:** Register → Login → SRS Generator → Monitor job → Download
- **Supported Formats:** Input PDF/DOCX, Output .docx (PDF coming soon)
- **Domain Chooser:** 9 pre-built industry verticals
- **Quality Levels:** High-level, Technical, Enterprise
- **Support:** Contact form, FAQs, Email

### For Developers
- **Tech Stack:** FastAPI, MongoDB, RabbitMQ, Groq API
- **Auth:** Session-based + Google OAuth
- **Job Processing:** Async with RabbitMQ + background workers
- **APIs:** Fully RESTful, JSON request/response
- **Deployment:** Docker-ready, environment-configurable

### For Administrators
- **Monitoring:** Access MongoDB for job history
- **Configuration:** Environment variables for all settings
- **Email:** SMTP settings configurable
- **Scaling:** Horizontal scaling via additional workers
- **Security:** Bcrypt password hashing, HttpOnly cookies, CSRF protection

---

## ✅ Summary of All Features

| Feature | Category | API Endpoint | Status |
|---------|----------|--------------|--------|
| User Registration | Auth | POST /auth/register | ✅ Live |
| Username/Password Login | Auth | POST /auth/login | ✅ Live |
| Google OAuth Login | Auth | GET /auth/google/login | ✅ Live |
| Session Management | Auth | Built-in | ✅ Live |
| Problem Statement Enhancement | Generation | POST /enhance-problem-statement | ✅ Live |
| Auto-Generate Section | Generation | POST /auto-generate-section | ✅ Live |
| Full SRS Generation (7-step) | Generation | POST /generate_srs | ✅ Live |
| Job Status Tracking | Job Mgmt | GET /job/{job_id}/status | ✅ Live |
| Live Status Stream (SSE) | Job Mgmt | GET /job/{job_id}/status/stream | ✅ Live |
| Document Download | Download | GET /job/{job_id}/download | ✅ Live |
| Document Upload (PDF/DOCX) | Upload | POST /upload/srs | ✅ Live |
| Document Parser | Parse | POST /parse/srs/{file_id} | ✅ Live |
| SRS Upgrader | Enhance | POST /upgrade/srs/{file_id}/... | ✅ Live |
| Section Analyzer | Enhance | POST /upgrade/srs/{file_id}/analyse | ✅ Live |
| Question Generator | Enhance | POST /upgrade/srs/{file_id}/questions | ✅ Live |
| Diagram Generation | Diagrams | POST /diagram/create | ✅ Live |
| Chatbot Q&A | Chat | POST /api/chat/query | ✅ Live |
| Architecture Diagrams (4 types) | Diagrams | Included in SRS | ✅ Live |
| Email Delivery | Communication | Built-in to job completion | ✅ Live |
| Contact Form | Support | POST /api/contact | ✅ Live |
| Workspace/History | Document Mgmt | Web UI (Job Tracker) | ✅ Live |
| 9 Domain Schemas | Templates | System-wide | ✅ Live |
| Google OAuth Integration | Auth | OAuth 2.0 flow | ✅ Live |
| Real-time Job Tracking UI | UI | Web dashboard | ✅ Live |
| Responsive Web Interface | UI | All pages responsive | ✅ Live |
| PDF Export | Export | Planned | 🔄 Roadmap |

---

## 🔗 API Base URL

```
HTTP:  http://localhost:8000
HTTPS: https://yourdomain.com (production)
```

## 📚 Additional Resources

- Full API Documentation: [api.md](api.md)
- Implementation Plan: [implementation_plan.md](implementation_plan.md)
- Getting Started Guide: [startup_guide.md](startup_guide.md)
- Logging Guide: [LOGGING_QUICK_REF.md](LOGGING_QUICK_REF.md)

---

**Last Updated:** April 2026  
**License:** MIT  
**For Support:** Use contact form or refer to FAQs
