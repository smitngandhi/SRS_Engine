from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional

from srs_engine.core.logging import get_context_logger

logger = get_context_logger(__name__)


class TraceEvent:
    """Represents a single trace event in the execution flow."""
    
    def __init__(
        self,
        event_type: str,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        status: str = "running",
        data: Optional[Dict[str, Any]] = None,
        session_id: Optional[str] = None,
        timestamp: Optional[str] = None
    ):
        self.timestamp = timestamp or datetime.utcnow().isoformat()
        self.event_type = event_type
        self.agent_name = agent_name
        self.tool_name = tool_name
        self.status = status  # running, completed, failed
        self.data = data or {}
        self.session_id = session_id
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace event to dictionary for JSON serialization."""
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "agent_name": self.agent_name,
            "tool_name": self.tool_name,
            "status": self.status,
            "data": self.data,
            "session_id": self.session_id
        }


class TraceManager:
    """Manages trace events and WebSocket broadcasting for live execution traces."""
    
    def __init__(self):
        self.active_traces: Dict[str, List[TraceEvent]] = {}
        self.websocket_manager = None
        self._lock = asyncio.Lock()
    
    def set_websocket_manager(self, manager):
        """Set the WebSocket manager for broadcasting traces."""
        self.websocket_manager = manager
    
    async def emit_trace(
        self,
        session_id: str,
        event_type: str,
        agent_name: Optional[str] = None,
        tool_name: Optional[str] = None,
        status: str = "running",
        data: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Emit a trace event for live UI updates.
        
        Args:
            session_id: Unique session identifier
            event_type: Type of event (workflow_start, agent_start, agent_complete, etc.)
            agent_name: Name of the agent (if applicable)
            tool_name: Name of the tool being executed (if applicable)
            status: Current status (running, completed, failed)
            data: Additional event data
        """
        async with self._lock:
            trace_event = TraceEvent(
                session_id=session_id,
                event_type=event_type,
                agent_name=agent_name,
                tool_name=tool_name,
                status=status,
                data=data
            )
            
            # Store trace event
            if session_id not in self.active_traces:
                self.active_traces[session_id] = []
            self.active_traces[session_id].append(trace_event)
            
            print(f"🔥 TRACE EMITTED: {event_type} | agent={agent_name} | tool={tool_name} | status={status} | session={session_id}")
            logger.debug(
                f"emit_trace | {event_type} | agent={agent_name} | "
                f"status={status} | session={session_id}"
            )
            
            # Broadcast to WebSocket clients
            if self.websocket_manager:
                print(f"📡 Broadcasting to WebSocket for session {session_id}")
                await self._broadcast_trace(session_id, trace_event)
            else:
                print(f"❌ No WebSocket manager available for session {session_id}")
    
    async def _broadcast_trace(self, session_id: str, trace_event: TraceEvent) -> None:
        """Broadcast trace event to WebSocket clients."""
        try:
            await self.websocket_manager.send_trace(session_id, trace_event.to_dict())
        except Exception as e:
            logger.error(f"_broadcast_trace | Failed to broadcast trace | error={e}")
    
    async def get_session_traces(self, session_id: str) -> List[Dict[str, Any]]:
        """Get all trace events for a session."""
        async with self._lock:
            if session_id in self.active_traces:
                return [trace.to_dict() for trace in self.active_traces[session_id]]
            return []
    
    async def clear_session_traces(self, session_id: str) -> None:
        """Clear trace events for a session."""
        async with self._lock:
            if session_id in self.active_traces:
                del self.active_traces[session_id]
            logger.debug(f"clear_session_traces | Cleared traces for session={session_id}")
    
    async def emit_workflow_start(self, session_id: str, phase: int, agents: List[str]) -> None:
        """Emit workflow start event."""
        await self.emit_trace(
            session_id=session_id,
            event_type="workflow_start",
            status="running",
            data={
                "phase": phase,
                "agents": agents,
                "total_agents": len(agents)
            }
        )
    
    async def emit_agent_start(self, session_id: str, agent_name: str) -> None:
        """Emit agent start event."""
        await self.emit_trace(
            session_id=session_id,
            event_type="agent_start",
            agent_name=agent_name,
            status="running"
        )
    
    async def emit_agent_complete(self, session_id: str, agent_name: str, output_key: str) -> None:
        """Emit agent completion event."""
        await self.emit_trace(
            session_id=session_id,
            event_type="agent_complete",
            agent_name=agent_name,
            status="completed",
            data={"output_key": output_key}
        )
    
    async def emit_agent_error(self, session_id: str, agent_name: str, error: str) -> None:
        """Emit agent error event."""
        await self.emit_trace(
            session_id=session_id,
            event_type="agent_error",
            agent_name=agent_name,
            status="failed",
            data={"error": error}
        )
    
    async def emit_tool_execution(self, session_id: str, tool_name: str, status: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Emit tool execution event."""
        await self.emit_trace(
            session_id=session_id,
            event_type="tool_execution",
            tool_name=tool_name,
            status=status,
            data=data
        )
    
    async def emit_workflow_complete(self, session_id: str, phase: int, total_time: Optional[float] = None) -> None:
        """Emit workflow completion event."""
        await self.emit_trace(
            session_id=session_id,
            event_type="workflow_complete",
            status="completed",
            data={
                "phase": phase,
                "total_time": total_time
            }
        )


# Global trace manager instance
trace_manager = TraceManager()
