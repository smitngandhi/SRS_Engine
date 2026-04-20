# Project Buckets & Diagram Studio - Complete Feature Guide

Last Updated: April 2026
Version: 1.0
Audience: Developers, Project Managers, End Users

---

## Table of Contents

1. Overview
2. Project Buckets
3. Diagram Studio
4. Integration and Workflows
5. Technical Architecture
6. API Reference
7. User Workflows
8. Administration

---

## Overview

Project Buckets and Diagram Studio are two complementary features in SRS Engine that work together to provide a complete project management and visualization experience:

- Project Buckets: Central hub for organizing all project-related assets (SRS documents, diagrams, upgrades, versions)
- Diagram Studio: Professional tool for creating, editing, and versioning Mermaid diagrams tied to projects

Together, they enable teams to:
- Organize specifications and diagrams by project
- Track multiple versions of both documents and diagrams
- Visualize system architecture, workflows, and data models
- Maintain a single source of truth for project assets
- Share and collaborate on specifications

---

## Project Buckets

### What is a Project Bucket?

A Project Bucket is a unified container that brings together all assets related to a single project.

### Key Features

#### 1. Unified Dashboard

The Project Buckets interface provides a single view showing:
- Project name and description
- Quick statistics (number of documents, diagrams, versions)
- Recent activity timeline
- Team members and access controls
- Quick action buttons (view, download, share, archive)

#### 2. Four-Tab Interface

Tab 1 - Overview Tab:
- Project summary and metadata
- Key statistics and metrics
- Recent modifications timeline
- Quick access to most-used documents

Tab 2 - SRS Documents Tab:
- List of all SRS documents for the project
- Filter by version (Original, Enhanced, Upgraded)
- Document metadata (size, date, author)
- Action buttons (download, preview, delete, compare)

Tab 3 - Diagrams Tab:
- Gallery view of all project diagrams
- Thumbnail previews of each diagram
- Diagram type and version info
- Quick edit and export options

Tab 4 - History Tab:
- Complete version history of all assets
- Timeline view showing when each asset was created/modified
- Detailed change logs
- Version comparison capability

#### 3. Document Organization

Within the SRS Documents tab:
- Original SRS (generated from 7-step form)
- Enhanced SRS (with AI improvements)
- Upgraded SRS (from upgrader feature)
- Custom SRS versions (from regeneration)

Each document entry shows:
- Document name and version number
- Generation date and time
- File size
- Status (active, archived, deleted)
- Download option

#### 4. Diagram Organization

Within the Diagrams tab:
- Diagram type (flowchart, sequence, class, state, etc.)
- Diagram version and status
- Thumbnail preview (SVG rendered in browser)
- Edit and export options
- Delete option

#### 5. Version Tracking

Complete history showing:
- When each asset was created/modified
- What type of change (new, enhanced, regenerated)
- Comparison between versions
- Rollback capability (restore previous version)
- Timestamp and author information

#### 6. Search and Filter

- Filter documents by type (Original, Enhanced, Upgraded)
- Filter diagrams by type (Flowchart, Sequence, etc.)
- Search by keyword/date range
- Sort by date, name, or size

#### 7. Statistics Dashboard

Real-time metrics:
- Total SRS documents generated
- Total diagrams created
- Total versions across all assets
- Last modified timestamp
- Average document/diagram size

### How Project Buckets Work

User Flow:

1. User Logs In
   - Navigate to Project Buckets (/project-buckets)

2. Left Panel: Select Project
   - List of all user's projects
   - Shows project name and brief stats
   - Click to select/view

3. Right Panel: View Project Details
   - Project header with name and description
   - Key statistics (docs, diagrams, versions)
   - Tabbed interface:
     * Overview tab (project summary)
     * SRS Documents tab (all docs)
     * Diagrams tab (all diagrams with previews)
     * History tab (version timeline)
   - Action buttons (download, delete, edit)

4. Manage Assets
   - Download: GET /job/{job_id}/download
   - Preview: View inline SVG preview
   - Delete: Soft-delete from bucket
   - Compare: Side-by-side version comparison

5. Organize and Archive
   - Rename project
   - Add project description
   - Archive old documents
   - Export entire bucket as ZIP

---

## Diagram Studio

### What is Diagram Studio?

Diagram Studio is a professional tool for creating, editing, and versioning Mermaid diagrams with AI assistance. It provides:

- AI-Powered Generation: Generate diagrams from natural language prompts
- Live Editing: Edit Mermaid code with real-time preview
- Version Control: Track all versions of each diagram
- Project Integration: Link diagrams to specific projects
- Multiple Formats: Export as SVG, PNG, or embedded Mermaid
- Export Options: Download for use in documentation or presentations

### Three-Panel Interface

Panel 1 - Input Controls (Left):
- Diagram type selector (Flowchart, Sequence, Class, State, ER, Git, Mindmap)
- AI Prompt input (natural language description)
- Version/iteration selector
- Generation options (layout, theme, size)
- Action buttons (Generate, Save, Delete)

Panel 2 - SVG Preview (Center):
- Live rendering of Mermaid diagram
- Real-time updates as code changes
- Zoom and pan controls
- Export buttons (SVG, PNG)
- Full-screen preview option

Panel 3 - Code Editor (Right):
- Mermaid code editor with syntax highlighting
- Line numbers and code formatting
- Quick snippets and auto-complete
- Save and revert options
- Code validation feedback

### Supported Diagram Types

1. Flowchart - Process flows, decision trees, workflows
2. Sequence Diagram - API calls, user interactions, system sequences
3. Class Diagram - Object-oriented design, data models
4. State Diagram - State machines, finite state automata
5. Entity Relationship (ER) - Database schema design
6. Git Diagram - Git workflow visualization
7. Mindmap - Hierarchical brainstorming, concept mapping

### Diagram Versioning

Each diagram stored in database with:
- diagram_id: Unique identifier
- project_id: Linked to specific project
- diagram_type: Type of diagram
- mermaid_code: Current code version
- created_at: Creation timestamp
- modified_at: Last modification timestamp
- version_history: Array of previous versions
- svg_preview: Cached SVG for quick rendering
- png_export: Cached PNG for download

### AI-Powered Generation

Process:
1. User enters natural language prompt
2. Groq API (LLM) analyzes prompt
3. LLM generates Mermaid code based on diagram type
4. Code rendered as SVG in real-time
5. User can edit code or regenerate with refined prompt
6. Save final diagram to project bucket

Example:
Input: "Create a flowchart for user registration process with email verification"
Output: Mermaid flowchart with user input, validation, email sending, confirmation steps

### Editing Workflow

1. Select diagram from project bucket or create new
2. Choose diagram type
3. Either:
   a. Enter natural language prompt for AI generation, OR
   b. Write/edit Mermaid code directly
4. See live SVG preview
5. Refine code or regenerate with new prompt
6. Save version when satisfied
7. Export as SVG, PNG, or embed in documentation

---

## Integration and Workflows

### How Project Buckets and Diagram Studio Work Together

#### Workflow 1: Create SRS and Diagrams for New Project

Steps:
1. User completes 7-step SRS generation form
2. System creates new project in Project Buckets
3. SRS document stored as v1.0 in project
4. Auto-generated architecture diagrams stored in project
5. User navigates to Project Buckets
6. Can create additional custom diagrams in Diagram Studio
7. All diagrams linked to same project
8. Project bucket shows unified view of SRS + all diagrams

Benefits:
- Complete project assets in one location
- Easy to share entire project with team
- All versions tracked automatically
- Single source of truth for specifications

#### Workflow 2: Enhance SRS and Diagrams Together

Steps:
1. User uploads existing SRS to upgrader
2. AI enhances weak sections
3. Enhanced SRS stored as new version in project
4. User accesses Project Buckets overview
5. Sees both original and enhanced documents
6. Decides to update architecture diagram
7. Navigates to Diagram Studio
8. Generates new diagram version based on enhanced content
9. New diagram version automatically stored in project
10. Project bucket shows updated versions

Benefits:
- Track relationship between document and diagram versions
- Maintain design consistency across updates
- Easy to compare old and new versions
- Collaborative feedback on improvements

#### Workflow 3: Share Project with Team

Steps:
1. User selects project in Project Buckets
2. Clicks "Share" button
3. Invites team members with specific roles:
   - Viewer: Can download and view
   - Commenter: Can add notes and feedback
   - Editor: Can modify documents and diagrams
4. Team members receive email invitation
5. Can access project and:
   - View SRS documents
   - View and comment on diagrams
   - Download complete bucket as ZIP
   - Propose changes (edit mode)
6. Owner reviews and approves changes
7. Version automatically incremented

Benefits:
- Centralized collaboration
- Clear audit trail of who changed what
- No scattered file versions
- Real-time team awareness

---

## Technical Architecture

### Database Schema

Collection: project_buckets

Fields:
- _id: ObjectId
- user_id: ObjectId
- project_name: String
- project_description: String
- created_at: Date
- updated_at: Date
- team_members: Array of objects with user_id, role, added_at
- tags: Array of strings
- metadata: Object with total_documents, total_diagrams, total_versions, last_accessed
- is_archived: Boolean
- storage_quota_used: Number

Collection: diagrams

Fields:
- _id: ObjectId
- user_id: ObjectId
- project_id: ObjectId
- project_name: String
- diagram_name: String
- diagram_type: String
- mermaid_code: String
- svg_preview: String
- png_url: String
- created_at: Date
- modified_at: Date
- version: Number
- version_history: Array of version objects
- tags: Array of strings
- is_archived: Boolean
- view_count: Number
- download_count: Number

---

## API Reference

### Base URL

http://localhost:8000 (development)
https://yourdomain.com (production)

### Project Buckets Endpoints

GET /api/project-buckets
Description: Returns list of all project buckets for authenticated user
Response: { buckets: [...] }

GET /api/project-buckets/{project_id}
Description: Returns complete project bucket details with all documents and diagrams
Response: { project_name, documents, diagrams, versions, team_members }

POST /api/project-buckets
Description: Create new project bucket
Request: { project_name, project_description, tags }
Response: { project_id, created_at }

PATCH /api/project-buckets/{project_id}
Description: Update project metadata
Request: { project_name, project_description }
Response: { success, updated_at }

DELETE /api/project-buckets/{project_id}
Description: Archive/delete project bucket
Response: { success, archived_at }

GET /api/project-buckets/{project_id}/documents
Description: List all SRS documents in project
Response: { documents: [...] }

GET /api/project-buckets/{project_id}/diagrams
Description: List all diagrams in project with thumbnails
Response: { diagrams: [...] }

GET /api/project-buckets/{project_id}/history
Description: Get complete version history of all assets
Response: { history: [...] }

POST /api/project-buckets/{project_id}/share
Description: Share project with team member
Request: { email, role }
Response: { success, shared_with }

### Diagram Studio Endpoints

POST /api/diagram/create
Description: Create new diagram in project
Request: { project_id, diagram_name, diagram_type, mermaid_code }
Response: { diagram_id, created_at }

GET /api/diagram/{diagram_id}
Description: Retrieve diagram details
Response: { diagram_name, diagram_type, mermaid_code, svg_preview, version_history }

POST /api/diagram/{diagram_id}/generate
Description: AI-generate diagram from prompt
Request: { prompt, diagram_type }
Response: { mermaid_code, svg_preview }

PATCH /api/diagram/{diagram_id}
Description: Update diagram code
Request: { mermaid_code, change_description }
Response: { success, version, modified_at }

POST /api/diagram/{diagram_id}/regenerate
Description: Regenerate diagram with new prompt
Request: { prompt }
Response: { mermaid_code, svg_preview, version }

GET /api/diagram/{diagram_id}/export
Description: Export diagram as PNG or SVG
Query: ?format=png or ?format=svg
Response: Binary file

DELETE /api/diagram/{diagram_id}
Description: Delete diagram version
Response: { success, deleted_at }

GET /api/diagram/{diagram_id}/versions
Description: Get all versions of specific diagram
Response: { versions: [...] }

POST /api/diagram/{diagram_id}/revert
Description: Revert to previous version
Request: { version_number }
Response: { success, reverted_at }

---

## User Workflows

### Complete Workflow: From SRS to Diagram

Step 1: Generate Initial SRS
- User completes 7-step form
- System generates SRS with architecture diagrams
- SRS stored in new project bucket

Step 2: Project Bucket Created Automatically
- Project bucket created with v1.0 SRS
- Auto-generated diagrams included
- User can see complete project in /project-buckets

Step 3: Access Project Bucket
- Navigate to /project-buckets
- Select project from left sidebar
- View Overview tab with statistics

Step 4: Explore SRS Versions
- Click "SRS Documents" tab
- See original SRS and any enhanced versions
- Download any version for review

Step 5: View Diagrams
- Click "Diagrams" tab
- See thumbnails of all project diagrams
- Preview each diagram

Step 6: Create Custom Diagram
- Click "Create New Diagram"
- Navigate to Diagram Studio
- Select diagram type (e.g., Sequence Diagram)
- Enter AI prompt: "Create sequence diagram for user login flow"
- AI generates Mermaid code
- Review SVG preview
- Save to project

Step 7: Edit Diagram
- Click Edit on diagram
- Modify Mermaid code directly
- See real-time SVG updates
- Save new version

Step 8: Export Diagram
- Click Export
- Choose format (PNG or SVG)
- Download for use in documentation

Step 9: Share Project with Team
- Click Share project button
- Invite team members by email
- Set access level (Viewer, Commenter, Editor)
- Team receives email invite
- Can view all project assets

Step 10: Track Changes
- Click "History" tab
- See timeline of all changes
- Compare versions side-by-side
- See who made what changes and when

---

## Administration

### Managing Project Buckets

For Administrators:

Monitor Disk Usage:
- Track total storage per user
- Alert when usage approaches quota
- Archive old projects to free space

User Access Control:
- Manage who can create project buckets
- Track project sharing activity
- Generate usage reports

Data Retention:
- Archive inactive projects after 90 days
- Hard-delete archived projects after 365 days
- Export user data on request

### Configuration

Environment Variables:

MAX_PROJECT_BUCKETS_PER_USER=100
MAX_DIAGRAMS_PER_PROJECT=500
MAX_VERSIONS_PER_DIAGRAM=20
PROJECT_STORAGE_QUOTA_GB=50
AUTO_ARCHIVE_DAYS=90

### Performance Optimization

Database Indexing:
- Index on project_id for fast lookups
- Index on user_id for permission checks
- Index on created_at for sorting
- Index on project_name for search

Caching Strategy:
- Cache SVG previews for 24 hours
- Cache project statistics for 1 hour
- Invalidate cache on update

---

## Summary

Project Buckets and Diagram Studio provide a comprehensive solution for managing SRS documents and architectural diagrams:

Key Features:
- Unified project dashboard
- Complete version history
- AI-powered diagram generation
- Real-time team collaboration
- Easy export and sharing

Benefits:
- Organized project assets
- Single source of truth
- Audit trail of all changes
- Professional diagram creation
- Seamless team collaboration

Next Steps:
- Explore Project Buckets interface
- Try Diagram Studio features
- Share project with team
- Generate and edit custom diagrams
- Monitor project statistics

For Support: Use contact form or refer to FAQs

Last Updated: April 2026
Version: 1.0
