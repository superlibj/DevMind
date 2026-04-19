"""
WebSocket chat handler for real-time AI agent communication.

This module provides WebSocket connection management and message handling
for real-time chat interface with the AI agent.
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Set

from fastapi import WebSocket, WebSocketDisconnect, status

from src.api.middleware.auth import auth_manager
from src.core.agent import ReactAgent, AgentMemory
from src.api.middleware.logging import agent_logger

logger = logging.getLogger(__name__)


class WebSocketConnectionManager:
    """Manages WebSocket connections and message broadcasting."""

    def __init__(self):
        """Initialize connection manager."""
        self.active_connections: Dict[str, WebSocket] = {}
        self.user_sessions: Dict[str, str] = {}  # user_id -> session_id
        self.session_users: Dict[str, str] = {}  # session_id -> user_id
        self.session_agents: Dict[str, ReactAgent] = {}  # session_id -> agent
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}  # session_id -> metadata

    async def connect(self, websocket: WebSocket, user_id: str, session_id: str, metadata: Optional[Dict[str, Any]] = None):
        """Connect a new WebSocket.

        Args:
            websocket: WebSocket connection
            user_id: User identifier
            session_id: Session identifier
            metadata: Optional connection metadata
        """
        await websocket.accept()

        # Close existing connection for this user if any
        if user_id in self.user_sessions:
            old_session_id = self.user_sessions[user_id]
            await self._disconnect_session(old_session_id, close_websocket=True)

        # Store connection
        self.active_connections[session_id] = websocket
        self.user_sessions[user_id] = session_id
        self.session_users[session_id] = user_id
        self.connection_metadata[session_id] = metadata or {}

        # Initialize agent with memory for this session
        memory = AgentMemory(session_id=session_id)
        agent = ReactAgent(memory=memory)
        self.session_agents[session_id] = agent

        logger.info(f"WebSocket connected: user_id={user_id}, session_id={session_id}")

    async def disconnect(self, session_id: str):
        """Disconnect a WebSocket session.

        Args:
            session_id: Session identifier
        """
        await self._disconnect_session(session_id, close_websocket=False)

    async def _disconnect_session(self, session_id: str, close_websocket: bool = False):
        """Internal method to disconnect a session.

        Args:
            session_id: Session identifier
            close_websocket: Whether to close the WebSocket connection
        """
        if session_id in self.active_connections:
            if close_websocket:
                try:
                    websocket = self.active_connections[session_id]
                    await websocket.close(code=status.WS_1000_NORMAL_CLOSURE)
                except Exception as e:
                    logger.warning(f"Error closing WebSocket for session {session_id}: {e}")

            del self.active_connections[session_id]

        # Clean up mappings
        if session_id in self.session_users:
            user_id = self.session_users[session_id]
            if user_id in self.user_sessions:
                del self.user_sessions[user_id]
            del self.session_users[session_id]

        if session_id in self.session_agents:
            del self.session_agents[session_id]

        if session_id in self.connection_metadata:
            del self.connection_metadata[session_id]

        logger.info(f"WebSocket disconnected: session_id={session_id}")

    async def send_message(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Send message to a specific session.

        Args:
            session_id: Session identifier
            message: Message to send

        Returns:
            True if message was sent successfully
        """
        if session_id not in self.active_connections:
            return False

        try:
            websocket = self.active_connections[session_id]
            await websocket.send_json(message)
            return True
        except Exception as e:
            logger.error(f"Failed to send message to session {session_id}: {e}")
            await self.disconnect(session_id)
            return False

    async def broadcast_to_user(self, user_id: str, message: Dict[str, Any]) -> bool:
        """Broadcast message to all sessions of a user.

        Args:
            user_id: User identifier
            message: Message to broadcast

        Returns:
            True if message was sent to at least one session
        """
        if user_id not in self.user_sessions:
            return False

        session_id = self.user_sessions[user_id]
        return await self.send_message(session_id, message)

    def get_active_sessions(self) -> Set[str]:
        """Get all active session IDs.

        Returns:
            Set of active session IDs
        """
        return set(self.active_connections.keys())

    def get_user_session(self, user_id: str) -> Optional[str]:
        """Get session ID for a user.

        Args:
            user_id: User identifier

        Returns:
            Session ID or None if user not connected
        """
        return self.user_sessions.get(user_id)

    def get_session_user(self, session_id: str) -> Optional[str]:
        """Get user ID for a session.

        Args:
            session_id: Session identifier

        Returns:
            User ID or None if session not found
        """
        return self.session_users.get(session_id)

    def get_connection_count(self) -> int:
        """Get total number of active connections.

        Returns:
            Number of active connections
        """
        return len(self.active_connections)


class ChatWebSocketHandler:
    """Handles WebSocket chat messages and agent interactions."""

    def __init__(self, connection_manager: WebSocketConnectionManager):
        """Initialize chat handler.

        Args:
            connection_manager: WebSocket connection manager
        """
        self.manager = connection_manager

    async def authenticate_websocket(self, token: Optional[str]) -> Optional[Dict[str, Any]]:
        """Authenticate WebSocket connection using JWT token.

        Args:
            token: JWT token

        Returns:
            User payload if authentication successful, None otherwise
        """
        if not token:
            return None

        try:
            payload = auth_manager.decode_token(token)
            user_id = payload.get("sub")
            if not user_id:
                return None
            return payload
        except Exception as e:
            logger.warning(f"WebSocket authentication failed: {e}")
            return None

    async def handle_connection(self, websocket: WebSocket, token: Optional[str] = None):
        """Handle new WebSocket connection.

        Args:
            websocket: WebSocket connection
            token: Authentication token
        """
        # Authenticate user
        user_payload = await self.authenticate_websocket(token)
        if not user_payload:
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION)
            return

        user_id = user_payload["sub"]
        username = user_payload.get("username", "Unknown")
        session_id = str(uuid.uuid4())

        # Connect WebSocket
        await self.manager.connect(
            websocket=websocket,
            user_id=user_id,
            session_id=session_id,
            metadata={
                "username": username,
                "permissions": user_payload.get("permissions", []),
                "connected_at": datetime.now(timezone.utc).isoformat()
            }
        )

        try:
            # Send welcome message
            await self.manager.send_message(session_id, {
                "type": "welcome",
                "message": f"Welcome {username}! How can I help you with your code today?",
                "session_id": session_id,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "user": {
                    "id": user_id,
                    "username": username,
                    "permissions": user_payload.get("permissions", [])
                }
            })

            # Handle messages
            await self._handle_messages(websocket, session_id, user_id)

        except WebSocketDisconnect:
            logger.info(f"WebSocket disconnected: user_id={user_id}, session_id={session_id}")
        except Exception as e:
            logger.error(f"WebSocket error for session {session_id}: {e}")
        finally:
            await self.manager.disconnect(session_id)

    async def _handle_messages(self, websocket: WebSocket, session_id: str, user_id: str):
        """Handle incoming WebSocket messages.

        Args:
            websocket: WebSocket connection
            session_id: Session identifier
            user_id: User identifier
        """
        agent = self.manager.session_agents.get(session_id)
        if not agent:
            logger.error(f"No agent found for session {session_id}")
            return

        while True:
            try:
                # Receive message with timeout
                data = await asyncio.wait_for(websocket.receive_json(), timeout=30.0)
                await self._process_message(data, session_id, user_id, agent)

            except asyncio.TimeoutError:
                # Send keepalive ping
                await self.manager.send_message(session_id, {
                    "type": "ping",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            except WebSocketDisconnect:
                break

            except json.JSONDecodeError as e:
                logger.warning(f"Invalid JSON from session {session_id}: {e}")
                await self.manager.send_message(session_id, {
                    "type": "error",
                    "message": "Invalid message format. Please send valid JSON.",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

            except Exception as e:
                logger.error(f"Error processing message for session {session_id}: {e}")
                await self.manager.send_message(session_id, {
                    "type": "error",
                    "message": "An error occurred while processing your message.",
                    "timestamp": datetime.now(timezone.utc).isoformat()
                })

    async def _process_message(
        self,
        data: Dict[str, Any],
        session_id: str,
        user_id: str,
        agent: ReactAgent
    ):
        """Process a received WebSocket message.

        Args:
            data: Message data
            session_id: Session identifier
            user_id: User identifier
            agent: Agent instance for this session
        """
        message_type = data.get("type", "message")
        timestamp = datetime.now(timezone.utc).isoformat()

        if message_type == "message":
            await self._handle_chat_message(data, session_id, user_id, agent, timestamp)

        elif message_type == "ping":
            # Respond to ping
            await self.manager.send_message(session_id, {
                "type": "pong",
                "timestamp": timestamp
            })

        elif message_type == "typing_start":
            # Handle typing indicator start
            await self._handle_typing_start(session_id, user_id, timestamp)

        elif message_type == "typing_stop":
            # Handle typing indicator stop
            await self._handle_typing_stop(session_id, user_id, timestamp)

        else:
            logger.warning(f"Unknown message type '{message_type}' from session {session_id}")
            await self.manager.send_message(session_id, {
                "type": "error",
                "message": f"Unknown message type: {message_type}",
                "timestamp": timestamp
            })

    async def _handle_chat_message(
        self,
        data: Dict[str, Any],
        session_id: str,
        user_id: str,
        agent: ReactAgent,
        timestamp: str
    ):
        """Handle chat message processing.

        Args:
            data: Message data
            session_id: Session identifier
            user_id: User identifier
            agent: Agent instance
            timestamp: Message timestamp
        """
        user_message = data.get("message", "").strip()
        context = data.get("context", {})

        if not user_message:
            await self.manager.send_message(session_id, {
                "type": "error",
                "message": "Message cannot be empty.",
                "timestamp": timestamp
            })
            return

        operation_id = str(uuid.uuid4())

        try:
            agent_logger.log_agent_operation(
                operation="websocket_chat",
                user_id=user_id,
                operation_id=operation_id,
                status="started",
                details={
                    "session_id": session_id,
                    "message_length": len(user_message)
                }
            )

            # Add user message to memory
            agent.memory.add_message("user", user_message)

            # Send typing indicator
            await self.manager.send_message(session_id, {
                "type": "typing",
                "message": "Agent is thinking...",
                "timestamp": timestamp
            })

            # Process message with agent
            response_data = await agent.process_request(
                message=user_message,
                context=context,
                user_id=user_id
            )

            # Add assistant response to memory
            agent.memory.add_message("assistant", response_data["response"])

            # Send response
            await self.manager.send_message(session_id, {
                "type": "response",
                "message": response_data["response"],
                "reasoning": response_data.get("reasoning"),
                "tools_used": response_data.get("tools_used"),
                "suggestions": response_data.get("suggestions"),
                "operation_id": operation_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

            agent_logger.log_agent_operation(
                operation="websocket_chat",
                user_id=user_id,
                operation_id=operation_id,
                status="completed",
                details={
                    "session_id": session_id,
                    "response_length": len(response_data["response"]),
                    "tools_used": response_data.get("tools_used", [])
                }
            )

        except Exception as e:
            agent_logger.log_agent_operation(
                operation="websocket_chat",
                user_id=user_id,
                operation_id=operation_id,
                status="failed",
                error=str(e)
            )

            logger.error(f"Chat processing failed for session {session_id}: {e}")
            await self.manager.send_message(session_id, {
                "type": "error",
                "message": "Sorry, I encountered an error processing your request. Please try again.",
                "operation_id": operation_id,
                "timestamp": datetime.now(timezone.utc).isoformat()
            })

    async def _handle_typing_start(self, session_id: str, user_id: str, timestamp: str):
        """Handle typing indicator start.

        Args:
            session_id: Session identifier
            user_id: User identifier
            timestamp: Message timestamp
        """
        # For now, just acknowledge the typing start
        # In a multi-user chat, this could be broadcast to other participants
        pass

    async def _handle_typing_stop(self, session_id: str, user_id: str, timestamp: str):
        """Handle typing indicator stop.

        Args:
            session_id: Session identifier
            user_id: User identifier
            timestamp: Message timestamp
        """
        # For now, just acknowledge the typing stop
        # In a multi-user chat, this could be broadcast to other participants
        pass


# Global connection manager and chat handler
connection_manager = WebSocketConnectionManager()
chat_handler = ChatWebSocketHandler(connection_manager)