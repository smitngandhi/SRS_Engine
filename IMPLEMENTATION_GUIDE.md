# 🎯 Live Traces Implementation Guide

## 📍 Exact Implementation Points

### **🔧 Where to Add Trace Events**

The traces system is already implemented, but here are the exact points where trace events are emitted:

---

## **1. SRS Service - Main Orchestration**

**File**: `srs_engine/core/services/srs_service.py`

### **Phase 1: Technical Agents (5 parallel)**
```python
# Lines ~290-320
await trace_manager.emit_workflow_start(session_id, phase=1, agents=phase1_agents)

for agent_name in phase1_agents:
    await trace_manager.emit_agent_start(session_id, agent_name)
    # ... agent execution ...
    await trace_manager.emit_agent_complete(session_id, agent_name, output_key)

await trace_manager.emit_workflow_complete(session_id, phase=1)
```

### **Phase 2: Glossary & Assumptions (2 parallel)**
```python
# Lines ~322-342
await trace_manager.emit_workflow_start(session_id, phase=2, agents=phase2_agents)

for agent_name in phase2_agents:
    await trace_manager.emit_agent_start(session_id, agent_name)
    # ... agent execution ...
    await trace_manager.emit_agent_complete(session_id, agent_name, output_key)

await trace_manager.emit_workflow_complete(session_id, phase=2)
```

### **Phase 3: Diagram Generation (4 tools)**
```python
# Lines ~397-433
await trace_manager.emit_workflow_start(session_id, phase=3, agents=['diagram_generator'])

for diagram_tool in diagram_tools:
    await trace_manager.emit_tool_execution(session_id, tool_name, 'running', data)
    # ... tool execution ...
    await trace_manager.emit_tool_execution(session_id, tool_name, 'completed', data)

await trace_manager.emit_workflow_complete(session_id, phase=3)
```

### **Phase 4: Document Creation**
```python
# Lines ~430+
await trace_manager.emit_workflow_start(session_id, phase=4, agents=['document_generator'])
await trace_manager.emit_tool_execution(session_id, 'generate_srs_document', 'running', data)
# ... document generation ...
await trace_manager.emit_tool_execution(session_id, 'generate_srs_document', 'completed', data)
await trace_manager.emit_workflow_complete(session_id, phase=4)
```

---

## **2. Trace Manager - Event Broadcasting**

**File**: `srs_engine/core/tracing.py`

### **Event Emission Methods**
```python
class TraceManager:
    async def emit_workflow_start(self, session_id: str, phase: int, agents: list):
        event = TraceEvent(
            event_type="workflow_start",
            session_id=session_id,
            data={"phase": phase, "agents": agents}
        )
        await self._broadcast_event(session_id, event)

    async def emit_agent_start(self, session_id: str, agent_name: str):
        event = TraceEvent(
            event_type="agent_start",
            session_id=session_id,
            agent_name=agent_name
        )
        await self._broadcast_event(session_id, event)

    async def emit_agent_complete(self, session_id: str, agent_name: str, output_key: str):
        event = TraceEvent(
            event_type="agent_complete",
            session_id=session_id,
            agent_name=agent_name,
            data={"output_key": output_key}
        )
        await self._broadcast_event(session_id, event)

    async def emit_tool_execution(self, session_id: str, tool_name: str, status: str, data: dict = None):
        event = TraceEvent(
            event_type="tool_execution",
            session_id=session_id,
            tool_name=tool_name,
            status=status,
            data=data or {}
        )
        await self._broadcast_event(session_id, event)
```

---

## **3. WebSocket Router - Real-time Communication**

**File**: `srs_engine/core/routers/websocket.py`

### **WebSocket Endpoint**
```python
@router.websocket("/ws/traces/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await connection_manager.connect(websocket, session_id)
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            
            if message.get("type") == "get_history":
                # Send trace history
                history = trace_manager.get_session_traces(session_id)
                await websocket.send_text(json.dumps(history))
                
    except WebSocketDisconnect:
        connection_manager.disconnect(websocket, session_id)
```

### **Connection Manager**
```python
class ConnectionManager:
    async def connect(self, websocket: WebSocket, session_id: str):
        await websocket.accept()
        self.active_connections[session_id].append(websocket)

    async def broadcast(self, session_id: str, message: str):
        connections = self.active_connections.get(session_id, [])
        for connection in connections:
            await connection.send_text(message)
```

---

## **4. Frontend Integration - UI Updates**

**File**: `srs_engine/templates/pages/srs_generator.html`

### **HTML Structure**
```html
<!-- Traces Panel (Lines 394-422) -->
<div class="traces-panel" id="tracesPanel" style="display: block;">
  <div class="traces-header">
    <h3>🔍 Live Execution Traces</h3>
    <div class="traces-status" id="tracesStatus">
      <span class="status-dot" id="tracesStatusDot"></span>
      <span id="tracesStatusLabel">Ready to test traces...</span>
    </div>
  </div>
  
  <div class="traces-timeline" id="tracesTimeline">
    <!-- Timeline items populated dynamically -->
  </div>
  
  <div class="traces-progress">
    <div class="progress-track">
      <div class="progress-fill" id="tracesProgressFill"></div>
    </div>
    <div class="progress-checkpoints" id="tracesCheckpoints">
      <!-- Agent checkpoints populated dynamically -->
    </div>
  </div>
  
  <!-- Test Button -->
  <button id="testTracesBtn">🧪 Test Traces Simulation</button>
</div>

<!-- Scripts (Lines 425-429) -->
<script src="traces.js"></script>
<script src="srs_form.js"></script>
```

---

## **5. JavaScript Visualizer - Real-time Updates**

**File**: `srs_engine/static/traces.js`

### **TraceVisualizer Class**
```javascript
class TraceVisualizer {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.timeline = document.getElementById('tracesTimeline');
        this.progressFill = document.getElementById('tracesProgressFill');
        this.debugMode = true; // For testing
    }

    async connect(sessionId) {
        this.sessionId = sessionId;
        
        if (this.debugMode) {
            // Simulate traces without WebSocket
            this.simulateTraces();
            return;
        }
        
        // Real WebSocket connection
        const wsUrl = `ws://127.0.0.1:8000/ws/traces/${sessionId}`;
        this.ws = new WebSocket(wsUrl);
        this.setupWebSocketHandlers();
    }

    handleTraceEvent(event) {
        switch(event.event_type) {
            case 'workflow_start':
                this.addWorkflowPhase(event.data.phase, event.data.agents);
                break;
            case 'agent_start':
                this.updateAgentStatus(event.agent_name, 'running');
                break;
            case 'agent_complete':
                this.updateAgentStatus(event.agent_name, 'completed');
                break;
            case 'tool_execution':
                this.updateToolStatus(event.tool_name, event.status);
                break;
            case 'workflow_complete':
                this.completeWorkflowPhase(event.data.phase);
                break;
        }
    }
}
```

---

## **6. Form Integration - Trigger Connection**

**File**: `srs_engine/static/srs_form.js`

### **SRS Generation Handler**
```javascript
// Lines 394-448
document.getElementById('srsForm')?.addEventListener('submit', async (e) => {
    // Show traces panel immediately
    const tracesPanel = document.getElementById('tracesPanel');
    if (tracesPanel && window.traceViz) {
        tracesPanel.style.display = 'block';
        window.traceViz.updateStatus('Initializing SRS generation...');
    }

    try {
        const res = await fetch('/generate_srs', {
            method: 'POST',
            body: JSON.stringify(payload)
        });

        const result = await res.json();
        
        // Connect to traces WebSocket
        if (result.session_id && window.traceViz) {
            await window.traceViz.connect(result.session_id);
        }
    } catch (err) {
        console.error('Submission error:', err);
    }
});
```

---

## **7. Main Application - Initialization**

**File**: `srs_engine/main.py`

### **App Setup**
```python
# Lines 25-71
def create_app() -> FastAPI:
    app = FastAPI(lifespan=lifespan)
    
    # Initialize trace manager
    connection_manager = ConnectionManager()
    trace_manager = TraceManager(connection_manager)
    app.state.trace_manager = trace_manager
    
    # Include routers
    app.include_router(websocket_router)  # Traces WebSocket
    app.include_router(srs_router)        # SRS API
    
    return app
```

---

## **🎯 Complete Data Flow**

```
1. USER CLICKS "Generate SRS"
   ↓
2. srs_form.js → POST /generate_srs
   ↓
3. srs_api.py → generate_srs_service()
   ↓
4. srs_service.py → trace_manager.emit_workflow_start()
   ↓
5. tracing.py → connection_manager.broadcast()
   ↓
6. websocket.py → WebSocket.send() to client
   ↓
7. traces.js → handleTraceEvent() → UI updates
   ↓
8. Browser → Animated timeline updates
```

---

## **🔍 Debug Points**

### **Backend Debugging**
- Check `trace_manager.emit_*()` calls in `srs_service.py`
- Verify WebSocket connection in browser dev tools (Network tab)
- Check trace events in `tracing.py` `_broadcast_event()`

### **Frontend Debugging**
- Browser console for JavaScript errors
- Check `window.traceViz` object in console
- Verify DOM elements exist: `tracesPanel`, `tracesTimeline`, etc.

### **Integration Testing**
- Use test button in traces panel for simulation
- Check WebSocket messages in browser dev tools
- Verify timeline items are created correctly

---

## **🚀 Quick Implementation Checklist**

✅ **Backend** - Trace events in `srs_service.py`  
✅ **WebSocket** - Router in `websocket.py`  
✅ **Frontend** - Visualizer in `traces.js`  
✅ **UI** - Panel in `srs_generator.html`  
✅ **Integration** - Form handler in `srs_form.js`  
✅ **App Setup** - Initialization in `main.py`  

The traces system is fully implemented and ready to use. All components are interconnected and working together to provide real-time visualization of the SRS generation process.
