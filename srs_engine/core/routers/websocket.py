from __future__ import annotations

import json
from typing import Dict

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from srs_engine.core.logging import get_context_logger

logger = get_context_logger(__name__)


class ConnectionManager:
    """Manages WebSocket connections for real-time trace broadcasting."""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = None  # Will be set when needed
    
    async def connect(self, websocket: WebSocket, session_id: str) -> None:
        """
        Accept and store a WebSocket connection.
        
        Args:
            websocket: The WebSocket connection
            session_id: Unique session identifier
        """
        await websocket.accept()
        self.active_connections[session_id] = websocket
        print(f"🔌 WebSocket connected | session_id={session_id} | total_connections={len(self.active_connections)}")
        logger.info(f"WebSocket connected | session_id={session_id} | total_connections={len(self.active_connections)}")
    
    def disconnect(self, session_id: str) -> None:
        """
        Remove a WebSocket connection.
        
        Args:
            session_id: Session identifier to disconnect
        """
        if session_id in self.active_connections:
            del self.active_connections[session_id]
            logger.info(f"WebSocket disconnected | session_id={session_id} | total_connections={len(self.active_connections)}")
    
    async def send_trace(self, session_id: str, trace_event: Dict) -> None:
        """
        Send a trace event to a specific session.
        
        Args:
            session_id: Target session identifier
            trace_event: Trace event data to send
        """
        print(f"📡 WebSocket: Attempting to send trace to session {session_id}: {trace_event.get('event_type')}")
        if session_id in self.active_connections:
            try:
                await self.active_connections[session_id].send_text(json.dumps(trace_event))
                print(f"✅ WebSocket: Trace sent successfully to session {session_id} | event_type={trace_event.get('event_type')}")
                logger.debug(f"Trace sent | session_id={session_id} | event_type={trace_event.get('event_type')}")
            except Exception as e:
                print(f"❌ WebSocket: Failed to send trace to session {session_id} | error={e}")
                logger.error(f"Failed to send trace | session_id={session_id} | error={e}")
                # Remove broken connection
                self.disconnect(session_id)
        else:
            print(f"⚠️ WebSocket: No active connection for session {session_id}")
            logger.debug(f"No active connection for session | session_id={session_id}")
    
    async def broadcast_to_all(self, trace_event: Dict) -> None:
        """
        Broadcast a trace event to all active connections.
        
        Args:
            trace_event: Trace event data to broadcast
        """
        disconnected_sessions = []
        
        for session_id, websocket in self.active_connections.items():
            try:
                await websocket.send_text(json.dumps(trace_event))
            except Exception as e:
                logger.error(f"Broadcast failed | session_id={session_id} | error={e}")
                disconnected_sessions.append(session_id)
        
        # Clean up broken connections
        for session_id in disconnected_sessions:
            self.disconnect(session_id)
    
    def get_connection_count(self) -> int:
        """Get the number of active WebSocket connections."""
        return len(self.active_connections)
    
    def is_connected(self, session_id: str) -> bool:
        """Check if a session has an active WebSocket connection."""
        return session_id in self.active_connections


# Global connection manager instance
connection_manager = ConnectionManager()

# Create router
router = APIRouter()


@router.websocket("/ws/traces/{session_id}")
async def websocket_traces(websocket: WebSocket, session_id: str):
    """
    WebSocket endpoint for real-time trace events.
    
    Args:
        websocket: WebSocket connection instance
        session_id: Unique session identifier for trace tracking
    """
    await connection_manager.connect(websocket, session_id)
    
    try:
        # Send initial connection confirmation
        await websocket.send_text(json.dumps({
            "event_type": "connection_established",
            "session_id": session_id,
            "timestamp": "connected"
        }))
        
        # Keep connection alive and handle incoming messages
        while True:
            try:
                # Wait for client messages (keep-alive or control messages)
                message = await websocket.receive_text()
                
                # Parse client message
                try:
                    client_data = json.loads(message)
                    logger.debug(f"WebSocket message received | session_id={session_id} | type={client_data.get('type')}")
                    
                    # Handle different client message types
                    if client_data.get("type") == "ping":
                        await websocket.send_text(json.dumps({"type": "pong"}))
                    elif client_data.get("type") == "get_history":
                        # Send trace history for this session
                        from srs_engine.core.tracing import trace_manager
                        history = await trace_manager.get_session_traces(session_id)
                        await websocket.send_text(json.dumps({
                            "type": "history",
                            "traces": history
                        }))
                    
                except json.JSONDecodeError:
                    logger.warning(f"Invalid JSON received | session_id={session_id} | message={message}")
                
            except WebSocketDisconnect:
                logger.info(f"WebSocket disconnect requested | session_id={session_id}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected unexpectedly | session_id={session_id}")
    except Exception as e:
        logger.error(f"WebSocket error | session_id={session_id} | error={e}")
    finally:
        # Clean up connection
        connection_manager.disconnect(session_id)
