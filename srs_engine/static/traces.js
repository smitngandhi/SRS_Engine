class TraceVisualizer {
    constructor() {
        this.ws = null;
        this.sessionId = null;
        this.timeline = document.getElementById('tracesTimeline');
        this.progressFill = document.getElementById('tracesProgressFill');
        this.checkpoints = document.getElementById('tracesCheckpoints');
        this.statusLabel = document.getElementById('tracesStatusLabel');
        this.statusDot = document.getElementById('tracesStatusDot');
        this.totalPhases = 4;
        this.completedPhases = 0;
        this.currentPhase = 0;
        this.activeAgents = new Set();
        this.completedAgents = new Set();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
        this.reconnectDelay = 1000;
        this.debugMode = false; // Set to true to simulate traces without WebSocket
    }
    
    async connect(sessionId) {
        this.sessionId = sessionId;
        
        // DEBUG MODE: Simulate traces without WebSocket
        if (this.debugMode) {
            console.log('DEBUG MODE: Simulating traces without WebSocket');
            this.updateConnectionStatus('running');
            this.setStatus('Simulating SRS generation...');
            
            // Simulate the traces after a short delay
            setTimeout(() => this.simulateTraces(), 1000);
            return;
        }
        
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/traces/${sessionId}`;
        
        console.log('Attempting WebSocket connection to:', wsUrl);
        
        try {
            this.ws = new WebSocket(wsUrl);
            this.setupWebSocketHandlers();
            
            // Show connection status
            this.updateConnectionStatus('connecting');
            console.log('WebSocket connection initiated');
            
        } catch (error) {
            console.error('Failed to connect to traces WebSocket:', error);
            this.updateConnectionStatus('error');
        }
    }
    
    // DEBUG: Simulate trace events for testing
    simulateTraces() {
        const events = [
            { type: 'workflow_start', data: { phase: 1, agents: ['introduction', 'overall_description', 'system_features', 'external_interfaces', 'nfr'] } },
            { type: 'agent_start', agent: 'introduction' },
            { type: 'agent_complete', agent: 'introduction' },
            { type: 'agent_start', agent: 'overall_description' },
            { type: 'agent_complete', agent: 'overall_description' },
            { type: 'agent_start', agent: 'system_features' },
            { type: 'agent_complete', agent: 'system_features' },
            { type: 'agent_start', agent: 'external_interfaces' },
            { type: 'agent_complete', agent: 'external_interfaces' },
            { type: 'agent_start', agent: 'nfr' },
            { type: 'agent_complete', agent: 'nfr' },
            { type: 'workflow_complete', data: { phase: 1 } },
            { type: 'workflow_start', data: { phase: 2, agents: ['glossary', 'assumptions'] } },
            { type: 'agent_start', agent: 'glossary' },
            { type: 'agent_complete', agent: 'glossary' },
            { type: 'agent_start', agent: 'assumptions' },
            { type: 'agent_complete', agent: 'assumptions' },
            { type: 'workflow_complete', data: { phase: 2 } },
            { type: 'workflow_start', data: { phase: 3, agents: ['diagram_generator'] } },
            { type: 'tool_execution', tool: 'render_mermaid_png_user_interfaces', status: 'running' },
            { type: 'tool_execution', tool: 'render_mermaid_png_user_interfaces', status: 'completed' },
            { type: 'tool_execution', tool: 'render_mermaid_png_hardware_interfaces', status: 'running' },
            { type: 'tool_execution', tool: 'render_mermaid_png_hardware_interfaces', status: 'completed' },
            { type: 'tool_execution', tool: 'render_mermaid_png_software_interfaces', status: 'running' },
            { type: 'tool_execution', tool: 'render_mermaid_png_software_interfaces', status: 'completed' },
            { type: 'tool_execution', tool: 'render_mermaid_png_communication_interfaces', status: 'running' },
            { type: 'tool_execution', tool: 'render_mermaid_png_communication_interfaces', status: 'completed' },
            { type: 'workflow_complete', data: { phase: 3 } },
            { type: 'workflow_start', data: { phase: 4, agents: ['document_generator'] } },
            { type: 'tool_execution', tool: 'generate_srs_document', status: 'running' },
            { type: 'tool_execution', tool: 'generate_srs_document', status: 'completed' },
            { type: 'workflow_complete', data: { phase: 4 } }
        ];
        
        let index = 0;
        const runNextEvent = () => {
            if (index < events.length) {
                const event = events[index];
                this.handleTraceEvent({
                    event_type: event.type,
                    agent_name: event.agent,
                    tool_name: event.tool,
                    status: event.status || 'running',
                    data: event.data || {},
                    timestamp: new Date().toISOString(),
                    session_id: this.sessionId
                });
                index++;
                setTimeout(runNextEvent, 800); // 800ms between events
            } else {
                this.showCompletionAnimation();
            }
        };
        
        runNextEvent();
    }
    
    setupWebSocketHandlers() {
        this.ws.onopen = () => {
            console.log('WebSocket connected successfully');
            this.updateConnectionStatus('connected');
            this.reconnectAttempts = 0;
            
            // Request trace history
            console.log('Requesting trace history...');
            this.ws.send(JSON.stringify({ type: 'get_history' }));
            
            // Start ping interval to keep connection alive
            this.pingInterval = setInterval(() => {
                if (this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({ type: 'ping' }));
                }
            }, 30000);
        };
        
        this.ws.onmessage = (event) => {
            console.log('WebSocket message received:', event.data);
            try {
                const data = JSON.parse(event.data);
                this.handleMessage(data);
            } catch (error) {
                console.error('Failed to parse WebSocket message:', error);
            }
        };
        
        this.ws.onclose = (event) => {
            console.log('WebSocket connection closed. Code:', event.code, 'Reason:', event.reason);
            this.updateConnectionStatus('disconnected');
            clearInterval(this.pingInterval);
            
            // Attempt to reconnect
            if (this.reconnectAttempts < this.maxReconnectAttempts) {
                setTimeout(() => {
                    this.reconnectAttempts++;
                    console.log(`Reconnecting attempt ${this.reconnectAttempts}/${this.maxReconnectAttempts}`);
                    this.connect(this.sessionId);
                }, this.reconnectDelay * this.reconnectAttempts);
            }
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateConnectionStatus('error');
        };
    }
    
    handleMessage(data) {
        switch (data.type) {
            case 'connection_established':
                console.log('WebSocket connection established');
                break;
            case 'history':
                this.loadTraceHistory(data.traces);
                break;
            case 'pong':
                // Ping response received
                break;
            default:
                this.handleTraceEvent(data);
        }
    }
    
    handleTraceEvent(trace) {
        switch (trace.event_type) {
            case 'workflow_start':
                this.startWorkflow(trace);
                break;
            case 'agent_start':
                this.startAgent(trace);
                break;
            case 'agent_complete':
                this.completeAgent(trace);
                break;
            case 'agent_error':
                this.agentError(trace);
                break;
            case 'tool_execution':
                this.showToolExecution(trace);
                break;
            case 'workflow_complete':
                this.completeWorkflow(trace);
                break;
        }
        
        // Scroll timeline to latest
        if (this.timeline) {
            this.timeline.scrollTop = this.timeline.scrollHeight;
        }
    }
    
    startWorkflow(trace) {
        this.currentPhase = trace.data.phase;
        this.updateConnectionStatus('running');
        
        // Create workflow header
        const workflowItem = this.createTimelineItem(
            `Phase ${trace.data.phase} Started`,
            'workflow_start',
            `Running ${trace.data.agents.length} agents: ${trace.data.agents.join(', ')}`
        );
        this.timeline.appendChild(workflowItem);
        
        // Initialize agent checkpoints for this phase
        this.initializeCheckpoints(trace.data.agents);
        
        // Update status
        this.updateStatus(`Phase ${trace.data.phase} - Running ${trace.data.agents.length} agents`);
    }
    
    startAgent(trace) {
        this.activeAgents.add(trace.agent_name);
        
        // Add to timeline
        const timelineItem = this.createTimelineItem(
            `${trace.agent_name} Agent`,
            'agent_start',
            'Processing...'
        );
        timelineItem.dataset.agent = trace.agent_name;
        this.timeline.appendChild(timelineItem);
        
        // Highlight checkpoint
        this.updateCheckpoint(trace.agent_name, 'active');
        
        // Update status
        this.updateStatus(`Phase ${this.currentPhase} - Running: ${Array.from(this.activeAgents).join(', ')}`);
    }
    
    completeAgent(trace) {
        this.activeAgents.delete(trace.agent_name);
        this.completedAgents.add(trace.agent_name);
        
        // Update timeline item
        const item = this.timeline.querySelector(`[data-agent="${trace.agent_name}"]`);
        if (item) {
            item.classList.remove('running');
            item.classList.add('completed');
            const statusElement = item.querySelector('.timeline-status');
            if (statusElement) {
                statusElement.textContent = 'Completed';
                statusElement.className = 'timeline-status completed';
            }
        }
        
        // Update checkpoint
        this.updateCheckpoint(trace.agent_name, 'completed');
        
        // Update progress
        this.updateProgress();
        
        // Update status
        const remaining = Array.from(this.activeAgents);
        if (remaining.length > 0) {
            this.updateStatus(`Phase ${this.currentPhase} - Running: ${remaining.join(', ')}`);
        } else {
            this.updateStatus(`Phase ${this.currentPhase} - Completing...`);
        }
    }
    
    agentError(trace) {
        this.activeAgents.delete(trace.agent_name);
        
        // Update timeline item
        const item = this.timeline.querySelector(`[data-agent="${trace.agent_name}"]`);
        if (item) {
            item.classList.remove('running');
            item.classList.add('error');
            const statusElement = item.querySelector('.timeline-status');
            if (statusElement) {
                statusElement.textContent = `Error: ${trace.data.error}`;
                statusElement.className = 'timeline-status error';
            }
        }
        
        // Update checkpoint
        this.updateCheckpoint(trace.agent_name, 'error');
        
        // Update status
        this.updateStatus(`Phase ${this.currentPhase} - Error in ${trace.agent_name}`);
    }
    
    showToolExecution(trace) {
        const toolItem = document.createElement('div');
        toolItem.className = `tool-execution ${trace.status}`;
        toolItem.innerHTML = `
            <div class="tool-icon">🔧</div>
            <div class="tool-details">
                <div class="tool-name">${trace.tool_name}</div>
                <div class="tool-status">${trace.status}</div>
                ${trace.data.progress ? `<div class="tool-progress">${trace.data.progress}</div>` : ''}
            </div>
        `;
        
        // Append to current workflow or agent item
        const currentWorkflow = this.timeline.querySelector('.timeline-item.workflow_start:last-child');
        const currentAgent = this.timeline.querySelector('.timeline-item.agent_start.running:last-child');
        
        if (currentAgent) {
            currentAgent.appendChild(toolItem);
        } else if (currentWorkflow) {
            currentWorkflow.appendChild(toolItem);
        } else {
            this.timeline.appendChild(toolItem);
        }
    }
    
    completeWorkflow(trace) {
        this.completedPhases++;
        
        // Add completion item
        const completionItem = this.createTimelineItem(
            `Phase ${trace.data.phase} Complete`,
            'workflow_complete',
            trace.data.total_time ? `Completed in ${trace.data.total_time.toFixed(2)}s` : 'Completed successfully'
        );
        this.timeline.appendChild(completionItem);
        
        // Update status
        if (this.completedPhases === this.totalPhases) {
            this.updateStatus('SRS Generation Complete!');
            this.showCompletionAnimation();
        } else {
            this.updateStatus(`Phase ${trace.data.phase} complete - ${this.totalPhases - this.completedPhases} phases remaining`);
        }
        
        // Clear active agents for this phase
        this.activeAgents.clear();
    }
    
    createTimelineItem(title, eventType, description) {
        const item = document.createElement('div');
        item.className = `timeline-item ${eventType}`;
        
        const icon = this.getEventIcon(eventType);
        const status = this.getEventStatus(eventType);
        
        item.innerHTML = `
            <div class="timeline-dot">
                <div class="status-dot ${status}">${icon}</div>
            </div>
            <div class="timeline-content">
                <div class="timeline-title">${title}</div>
                <div class="timeline-time">${new Date().toLocaleTimeString()}</div>
                ${description ? `<div class="timeline-description">${description}</div>` : ''}
                <div class="timeline-status ${status}">${this.getStatusText(eventType)}</div>
            </div>
        `;
        
        return item;
    }
    
    getEventIcon(eventType) {
        const icons = {
            'workflow_start': '🚀',
            'agent_start': '🤖',
            'agent_complete': '✅',
            'agent_error': '❌',
            'tool_execution': '🔧',
            'workflow_complete': '🎉'
        };
        return icons[eventType] || '📄';
    }
    
    getEventStatus(eventType) {
        const statusMap = {
            'workflow_start': 'running',
            'agent_start': 'running',
            'agent_complete': 'completed',
            'agent_error': 'error',
            'tool_execution': 'running',
            'workflow_complete': 'completed'
        };
        return statusMap[eventType] || 'running';
    }
    
    getStatusText(eventType) {
        const statusTexts = {
            'workflow_start': 'Starting',
            'agent_start': 'Processing',
            'agent_complete': 'Completed',
            'agent_error': 'Failed',
            'tool_execution': 'Executing',
            'workflow_complete': 'Complete'
        };
        return statusTexts[eventType] || 'Running';
    }
    
    initializeCheckpoints(agents) {
        if (!this.checkpoints) return;
        
        this.checkpoints.innerHTML = '';
        agents.forEach(agent => {
            const checkpoint = document.createElement('div');
            checkpoint.className = 'checkpoint';
            checkpoint.id = `checkpoint-${agent}`;
            checkpoint.innerHTML = `
                <div class="checkpoint-dot"></div>
                <div class="checkpoint-label">${agent}</div>
            `;
            this.checkpoints.appendChild(checkpoint);
        });
    }
    
    updateCheckpoint(agentName, status) {
        const checkpoint = document.getElementById(`checkpoint-${agentName}`);
        if (!checkpoint) return;
        
        checkpoint.className = `checkpoint ${status}`;
    }
    
    updateProgress() {
        if (!this.progressFill) return;
        
        const totalAgents = 7; // Total agents across all phases
        const completedCount = this.completedAgents.size;
        const progress = (completedCount / totalAgents) * 100;
        
        this.progressFill.style.width = `${progress}%`;
    }
    
    updateStatus(message) {
        if (this.statusLabel) {
            this.statusLabel.textContent = message;
        }
    }
    
    // Simple status update for immediate feedback
    setStatus(message) {
        if (this.statusLabel) {
            this.statusLabel.textContent = message;
        }
    }
    
    updateConnectionStatus(status) {
        if (!this.statusDot || !this.statusLabel) return;
        
        this.statusDot.className = `status-dot ${status}`;
        
        const statusMessages = {
            'connecting': 'Connecting to traces...',
            'connected': 'Connected to traces',
            'disconnected': 'Connection lost',
            'error': 'Connection error',
            'running': 'Generating SRS...',
            'completed': 'SRS Generation Complete!'
        };
        
        this.statusLabel.textContent = statusMessages[status] || status;
    }
    
    loadTraceHistory(traces) {
        traces.forEach(trace => this.handleTraceEvent(trace));
    }
    
    showCompletionAnimation() {
        const panel = document.getElementById('tracesPanel');
        if (panel) {
            panel.classList.add('completed');
            
            // Add confetti effect
            this.createConfetti();
            
            setTimeout(() => {
                panel.classList.remove('completed');
            }, 3000);
        }
    }
    
    createConfetti() {
        const panel = document.getElementById('tracesPanel');
        if (!panel) return;
        
        for (let i = 0; i < 20; i++) {
            const confetti = document.createElement('div');
            confetti.className = 'confetti';
            confetti.style.left = Math.random() * 100 + '%';
            confetti.style.animationDelay = Math.random() * 0.5 + 's';
            confetti.style.backgroundColor = `hsl(${Math.random() * 360}, 70%, 50%)`;
            panel.appendChild(confetti);
            
            setTimeout(() => confetti.remove(), 3000);
        }
    }
    
    disconnect() {
        if (this.ws) {
            this.ws.close();
            this.ws = null;
        }
        clearInterval(this.pingInterval);
    }
}

// Initialize trace visualizer immediately and also when DOM is ready
let traceViz = new TraceVisualizer();

// Also initialize on DOM ready to ensure it's available
document.addEventListener('DOMContentLoaded', () => {
    // Re-initialize if not already done
    if (!window.traceViz || !(window.traceViz instanceof TraceVisualizer)) {
        traceViz = new TraceVisualizer();
    }
    
    // Add test button handler
    const testBtn = document.getElementById('testTracesBtn');
    if (testBtn) {
        testBtn.addEventListener('click', () => {
            console.log('Test traces button clicked');
            if (traceViz) {
                traceViz.sessionId = 'test-session-' + Date.now();
                traceViz.simulateTraces();
            }
        });
    }
});

// Export for use in other scripts
window.TraceVisualizer = TraceVisualizer;
window.traceViz = traceViz;

console.log('✅ TraceVisualizer initialized:', window.traceViz);
