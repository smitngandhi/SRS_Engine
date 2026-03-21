# SRS Engine Architecture - Live Execution Traces Integration

## 🏗️ Overall System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        SRS ENGINE ARCHITECTURE                     │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   FRONTEND UI   │    │   FASTAPI APP   │    │   AI AGENTS     │
│                 │    │                 │    │                 │
│ • SRS Form      │◄──►│ • Routes        │◄──►│ • 7 Agents      │
│ • Traces Panel  │    │ • WebSocket     │    │ • ADK Framework │
│ • JavaScript    │    │ • Session Mgmt  │    │ • LLM Calls     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   BROWSER       │    │   BACKEND       │    │   AI SERVICES   │
│                 │    │                 │    │                 │
│ • WebSocket     │◄──►│ • TraceManager  │◄──►│ • SRS Service   │
│ • DOM Updates   │    │ • MongoDB       │    │ • Agent Orchest. │
│ • Animations    │    │ • Session Store │    │ • Document Gen   │
└─────────────────┘    └─────────────────┘    └─────────────────┘
```

## 🔄 Live Traces Data Flow

```
USER ACTION → SRS GENERATION → TRACE EVENTS → WEBSOCKET → FRONTEND → UI UPDATES

1. User clicks "Generate SRS"
       ↓
2. SRS Service starts orchestration
       ↓
3. TraceManager emits events
       ↓
4. WebSocket broadcasts to client
       ↓
5. JavaScript updates UI in real-time
```

## 📁 File Structure & Interconnections

### **Core Application Files**

```
srs_engine/
├── main.py                     # 🚀 FastAPI app entry point
├── core/
│   ├── tracing.py              # 🎯 TraceManager & TraceEvent
│   ├── routers/
│   │   ├── websocket.py        # 📡 WebSocket router for traces
│   │   ├── srs_api.py          # 🔌 SRS generation endpoints
│   │   ├── auth.py             # 🔐 Authentication routes
│   │   └── pages.py            # 📄 Page rendering
│   ├── services/
│   │   └── srs_service.py      # ⚙️ SRS generation logic
│   ├── auth/
│   │   └── deps.py             # 🔑 Authentication dependencies
│   └── db/
│       ├── mongo.py            # 🗄️ MongoDB connection
│       └── user_repo.py        # 👤 User repository
├── templates/pages/
│   └── srs_generator.html      # 🎨 Main UI with traces panel
└── static/
    ├── traces.js               # 🎬 Frontend trace visualizer
    ├── traces.css              # 🎨 Traces styling
    └── srs_form.js             # 📝 Form handling
```

## 🔗 Detailed Interconnections

### **1. Application Startup Flow**

```python
# main.py
┌─────────────────────────────────────────────────────────────┐
│ create_app()                                                │
│ ├─ init_mongo() → MongoDB connection                        │
│ ├─ trace_manager = TraceManager(connection_manager)         │
│ ├─ include_router(websocket_router)                         │
│ └─ include_router(srs_router)                               │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `main.py` - App initialization
- `core/db/mongo.py` - Database setup
- `core/tracing.py` - TraceManager creation

### **2. SRS Generation Flow**

```python
# srs_service.py
┌─────────────────────────────────────────────────────────────┐
│ generate_srs()                                              │
│ ├─ Create session_id                                        │
│ ├─ await trace_manager.emit_workflow_start()               │
│ ├─ Phase 1: Run 5 parallel agents                           │
│ │  ├─ await trace_manager.emit_agent_start()               │
│ │  └─ await trace_manager.emit_agent_complete()            │
│ ├─ Phase 2: Run 2 parallel agents                           │
│ ├─ Phase 3: Generate diagrams                              │
│ │  └─ await trace_manager.emit_tool_execution()            │
│ ├─ Phase 4: Create document                                 │
│ └─ Return session_id for WebSocket connection               │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `core/services/srs_service.py` - Main orchestration
- `core/tracing.py` - Trace event emission
- `core/routers/srs_api.py` - API endpoint

### **3. WebSocket Broadcasting Flow**

```python
# tracing.py + websocket.py
┌─────────────────────────────────────────────────────────────┐
│ TraceManager.emit_*()                                        │
│ ├─ Create TraceEvent object                                 │
│ ├─ Store in memory (session_traces)                        │
│ ├─ await connection_manager.broadcast(session_id, event)     │
│ └─ WebSocket sends JSON to client                           │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `core/tracing.py` - TraceManager
- `core/routers/websocket.py` - WebSocket handler

### **4. Frontend Visualization Flow**

```javascript
// traces.js
┌─────────────────────────────────────────────────────────────┐
│ TraceVisualizer                                              │
│ ├─ connect(session_id) → WebSocket connection               │
│ ├─ handleTraceEvent() → Process incoming events             │
│ ├─ updateTimeline() → Add timeline items                   │
│ ├─ updateProgress() → Update progress bar                  │
│ └─ showCompletionAnimation() → Confetti effect              │
└─────────────────────────────────────────────────────────────┘
```

**Key Files:**
- `static/traces.js` - TraceVisualizer class
- `static/traces.css` - Styling and animations
- `templates/pages/srs_generator.html` - UI structure

## 🎯 Trace Event Types & Flow

### **Event Hierarchy**

```
workflow_start (Phase 1)
├── agent_start (introduction)
├── agent_complete (introduction)
├── agent_start (overall_description)
├── agent_complete (overall_description)
├── agent_start (system_features)
├── agent_complete (system_features)
├── agent_start (external_interfaces)
├── agent_complete (external_interfaces)
├── agent_start (nfr)
├── agent_complete (nfr)
└── workflow_complete (Phase 1)

workflow_start (Phase 2)
├── agent_start (glossary)
├── agent_complete (glossary)
├── agent_start (assumptions)
├── agent_complete (assumptions)
└── workflow_complete (Phase 2)

workflow_start (Phase 3)
├── tool_execution (render_mermaid_png_user_interfaces)
├── tool_execution (render_mermaid_png_hardware_interfaces)
├── tool_execution (render_mermaid_png_software_interfaces)
├── tool_execution (render_mermaid_png_communication_interfaces)
└── workflow_complete (Phase 3)

workflow_start (Phase 4)
├── tool_execution (generate_srs_document)
└── workflow_complete (Phase 4)
```

## 🔧 Implementation Points

### **1. Where to Add Trace Events**

**In `core/services/srs_service.py`:**

```python
# Before agent execution
await trace_manager.emit_agent_start(session_id, agent_name)

# After agent execution  
await trace_manager.emit_agent_complete(session_id, agent_name, output_key)

# Before tool execution
await trace_manager.emit_tool_execution(session_id, tool_name, "running", data)

# After tool execution
await trace_manager.emit_tool_execution(session_id, tool_name, "completed", data)
```

### **2. WebSocket Connection Points**

**In `core/routers/websocket.py`:**

```python
@router.websocket("/ws/traces/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await connection_manager.connect(websocket, session_id)
    # Handle messages and broadcasting
```

### **3. Frontend Integration Points**

**In `templates/pages/srs_generator.html`:**

```html
<!-- Traces Panel -->
<div class="traces-panel" id="tracesPanel">
  <div class="traces-timeline" id="tracesTimeline"></div>
  <div class="traces-progress" id="tracesProgress"></div>
</div>

<!-- Scripts -->
<script src="traces.js"></script>
```

**In `static/srs_form.js`:**

```javascript
// Connect to traces after SRS generation starts
if (result.session_id && window.traceViz) {
    await window.traceViz.connect(result.session_id);
}
```

## 🚀 Data Flow Summary

```
1. USER ACTION (Generate SRS)
   ↓
2. API CALL (/generate_srs)
   ↓
3. SRS SERVICE (orchestration)
   ↓
4. TRACE MANAGER (emit events)
   ↓
5. WEBSOCKET (broadcast)
   ↓
6. FRONTEND (receive events)
   ↓
7. UI UPDATES (real-time visualization)
```

## 🎨 Frontend Components

### **TraceVisualizer Class Responsibilities**
- WebSocket connection management
- Event processing and UI updates
- Timeline item creation and animation
- Progress tracking
- Completion animations

### **UI Components**
- **Traces Panel**: Main container
- **Timeline**: Shows execution flow
- **Progress Bar**: Overall completion
- **Checkpoints**: Individual agent status
- **Status Indicator**: Connection status

## 🔍 Debug & Testing Points

### **Backend Testing**
- Check `trace_manager.emit_*()` calls in `srs_service.py`
- Verify WebSocket connection in browser dev tools
- Check trace event storage in memory

### **Frontend Testing**
- Browser console for JavaScript errors
- Network tab for WebSocket messages
- DOM inspection for panel visibility

### **Integration Testing**
- Full SRS generation workflow
- WebSocket message flow
- UI responsiveness and animations

This architecture provides a complete real-time visualization system that integrates seamlessly with the existing SRS Engine while maintaining clean separation of concerns.
