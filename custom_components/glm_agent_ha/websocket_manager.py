"""Secure WebSocket manager for GLM Agent HA integration."""

from __future__ import annotations

import json
import logging
from typing import Any, Dict, Set, Optional
import asyncio
from datetime import datetime

from homeassistant.core import HomeAssistant
from homeassistant.components.websocket_api import (
    ActiveConnection,
    async_register_command,
    websocket_command,
    require_admin,
)
from homeassistant.auth.models import User
from homeassistant.const import CONF_ID

from .security_manager import GLMAgentSecurityManager, ThreatType, SecurityLevel
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

class SecureWebSocketManager:
    """Secure WebSocket manager with proper authentication and authorization."""

    def __init__(self, hass: HomeAssistant, security_manager: GLMAgentSecurityManager):
        """Initialize the secure WebSocket manager.

        Args:
            hass: Home Assistant instance
            security_manager: Security manager instance
        """
        self.hass = hass
        self.security_manager = security_manager
        self._connections: Dict[str, ActiveConnection] = {}
        self._connection_users: Dict[str, User] = {}
        self._connection_last_activity: Dict[str, datetime] = {}

        # Register WebSocket commands
        self._register_websocket_commands()

    def _register_websocket_commands(self) -> None:
        """Register secure WebSocket commands."""
        # Register conversation entity WebSocket command
        async_register_command(
            self.hass,
            "glm_agent_conversation_subscribe",
            self._websocket_conversation_subscribe,
            require_admin(False)  # Allow authenticated users
        )

        # Register AI task entity WebSocket command
        async_register_command(
            self.hass,
            "glm_agent_ai_task_subscribe",
            self._websocket_ai_task_subscribe,
            require_admin(False)  # Allow authenticated users
        )

        # Register admin-only security monitoring command
        async_register_command(
            self.hass,
            "glm_agent_security_monitor",
            self._websocket_security_monitor,
            require_admin(True)  # Admin only
        )

    async def _validate_connection(self, connection: ActiveConnection) -> tuple[bool, Optional[str]]:
        """Validate WebSocket connection for security.

        Args:
            connection: WebSocket connection

        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check if user is authenticated
        if not connection.user or connection.user.id is None:
            self.security_manager._log_security_event(
                ThreatType.UNAUTHORIZED_ACCESS,
                SecurityLevel.HIGH,
                "websocket_validation",
                "Unauthenticated WebSocket connection attempt",
                connection_id=id(connection)
            )
            return False, "Authentication required"

        # Check rate limiting for this user
        user_id = str(connection.user.id)
        is_allowed, rate_info = self.security_manager.check_rate_limit(user_id, "websocket")

        if not is_allowed:
            self.security_manager._log_security_event(
                ThreatType.DOS,
                SecurityLevel.MEDIUM,
                "websocket_validation",
                f"WebSocket rate limit exceeded for user: {user_id}",
                user_id=user_id,
                rate_info=rate_info
            )
            return False, "Rate limit exceeded"

        # Check if user is blocked
        if self.security_manager.is_blocked(user_id):
            self.security_manager._log_security_event(
                ThreatType.UNAUTHORIZED_ACCESS,
                SecurityLevel.HIGH,
                "websocket_validation",
                f"Blocked user attempted WebSocket connection: {user_id}",
                user_id=user_id
            )
            return False, "Access denied"

        return True, None

    def _register_connection(self, connection: ActiveConnection) -> str:
        """Register a WebSocket connection.

        Args:
            connection: WebSocket connection

        Returns:
            Connection ID
        """
        connection_id = str(id(connection))
        self._connections[connection_id] = connection
        self._connection_users[connection_id] = connection.user
        self._connection_last_activity[connection_id] = datetime.now()

        _LOGGER.debug("WebSocket connection registered: %s for user: %s",
                     connection_id, connection.user.name if connection.user else "Unknown")

        return connection_id

    def _unregister_connection(self, connection_id: str) -> None:
        """Unregister a WebSocket connection.

        Args:
            connection_id: Connection ID to unregister
        """
        if connection_id in self._connections:
            del self._connections[connection_id]
        if connection_id in self._connection_users:
            del self._connection_users[connection_id]
        if connection_id in self._connection_last_activity:
            del self._connection_last_activity[connection_id]

        _LOGGER.debug("WebSocket connection unregistered: %s", connection_id)

    def _update_connection_activity(self, connection_id: str) -> None:
        """Update last activity timestamp for connection.

        Args:
            connection_id: Connection ID
        """
        if connection_id in self._connection_last_activity:
            self._connection_last_activity[connection_id] = datetime.now()

    async def _websocket_conversation_subscribe(self,
                                              hass: HomeAssistant,
                                              connection: ActiveConnection,
                                              msg: Dict[str, Any]) -> None:
        """Handle conversation entity WebSocket subscription.

        Args:
            hass: Home Assistant instance
            connection: WebSocket connection
            msg: WebSocket message
        """
        # Validate connection
        is_valid, error = await self._validate_connection(connection)
        if not is_valid:
            connection.send_error(msg["id"], "unauthorized", error)
            return

        # Register connection
        connection_id = self._register_connection(connection)

        try:
            # Subscribe to conversation entity updates
            entity_id = msg.get("entity_id")
            if not entity_id:
                connection.send_error(msg["id"], "invalid_format", "entity_id required")
                return

            # Validate entity ID format
            if not entity_id.startswith(f"{DOMAIN}."):
                connection.send_error(msg["id"], "invalid_format", "Invalid entity ID")
                return

            # Send initial state
            entity_state = hass.states.get(entity_id)
            if entity_state:
                connection.send_message({
                    "id": msg["id"],
                    "type": "event",
                    "event": {
                        "type": "state_changed",
                        "entity_id": entity_id,
                        "new_state": entity_state.as_dict(),
                        "old_state": None,
                        "timestamp": datetime.now().isoformat()
                    }
                })

            _LOGGER.info("WebSocket conversation subscription established: %s for entity: %s",
                        connection_id, entity_id)

        except Exception as e:
            _LOGGER.error("Error in conversation WebSocket subscription: %s", str(e))
            connection.send_error(msg["id"], "internal_error", str(e))
        finally:
            self._unregister_connection(connection_id)

    async def _websocket_ai_task_subscribe(self,
                                         hass: HomeAssistant,
                                         connection: ActiveConnection,
                                         msg: Dict[str, Any]) -> None:
        """Handle AI task entity WebSocket subscription.

        Args:
            hass: Home Assistant instance
            connection: WebSocket connection
            msg: WebSocket message
        """
        # Validate connection
        is_valid, error = await self._validate_connection(connection)
        if not is_valid:
            connection.send_error(msg["id"], "unauthorized", error)
            return

        # Register connection
        connection_id = self._register_connection(connection)

        try:
            # Subscribe to AI task entity updates
            entity_id = msg.get("entity_id")
            if not entity_id:
                connection.send_error(msg["id"], "invalid_format", "entity_id required")
                return

            # Validate entity ID format
            if not entity_id.startswith(f"{DOMAIN}."):
                connection.send_error(msg["id"], "invalid_format", "Invalid entity ID")
                return

            # Send initial state
            entity_state = hass.states.get(entity_id)
            if entity_state:
                connection.send_message({
                    "id": msg["id"],
                    "type": "event",
                    "event": {
                        "type": "state_changed",
                        "entity_id": entity_id,
                        "new_state": entity_state.as_dict(),
                        "old_state": None,
                        "timestamp": datetime.now().isoformat()
                    }
                })

            _LOGGER.info("WebSocket AI task subscription established: %s for entity: %s",
                        connection_id, entity_id)

        except Exception as e:
            _LOGGER.error("Error in AI task WebSocket subscription: %s", str(e))
            connection.send_error(msg["id"], "internal_error", str(e))
        finally:
            self._unregister_connection(connection_id)

    async def _websocket_security_monitor(self,
                                        hass: HomeAssistant,
                                        connection: ActiveConnection,
                                        msg: Dict[str, Any]) -> None:
        """Handle security monitoring WebSocket command (admin only).

        Args:
            hass: Home Assistant instance
            connection: WebSocket connection
            msg: WebSocket message
        """
        # Validate connection (admin check already done by decorator)
        is_valid, error = await self._validate_connection(connection)
        if not is_valid:
            connection.send_error(msg["id"], "unauthorized", error)
            return

        # Register connection
        connection_id = self._register_connection(connection)

        try:
            # Get security report
            hours = msg.get("hours", 24)
            security_report = self.security_manager.get_security_report(hours)

            connection.send_message({
                "id": msg["id"],
                "type": "result",
                "success": True,
                "result": security_report
            })

            _LOGGER.info("Security monitor WebSocket request processed: %s", connection_id)

        except Exception as e:
            _LOGGER.error("Error in security monitor WebSocket: %s", str(e))
            connection.send_error(msg["id"], "internal_error", str(e))
        finally:
            self._unregister_connection(connection_id)

    async def broadcast_entity_update(self, entity_id: str, old_state=None, new_state=None) -> None:
        """Broadcast entity state updates to subscribed WebSocket connections.

        Args:
            entity_id: Entity ID that was updated
            old_state: Previous state
            new_state: New state
        """
        if not self._connections:
            return

        message = {
            "type": "event",
            "event": {
                "type": "state_changed",
                "entity_id": entity_id,
                "new_state": new_state.as_dict() if new_state else None,
                "old_state": old_state.as_dict() if old_state else None,
                "timestamp": datetime.now().isoformat()
            }
        }

        # Send to all relevant connections
        disconnected_connections = []
        for connection_id, connection in self._connections.items():
            try:
                # Check if this connection should receive this update
                user = self._connection_users.get(connection_id)
                if user and hass.auth.async_user_can_access_entity(user, entity_id):
                    connection.send_message(message)
                    self._update_connection_activity(connection_id)
            except Exception as e:
                _LOGGER.warning("Failed to send WebSocket update to connection %s: %s",
                               connection_id, str(e))
                disconnected_connections.append(connection_id)

        # Clean up disconnected connections
        for connection_id in disconnected_connections:
            self._unregister_connection(connection_id)

    def get_connection_stats(self) -> Dict[str, Any]:
        """Get WebSocket connection statistics.

        Returns:
            Connection statistics
        """
        return {
            "total_connections": len(self._connections),
            "active_connections": len([
                conn_id for conn_id, last_activity in self._connection_last_activity.items()
                if (datetime.now() - last_activity).seconds < 300  # Active in last 5 minutes
            ]),
            "connections_by_user": {
                user.name if user else "Unknown": 1
                for user in self._connection_users.values()
            }
        }

    async def cleanup_stale_connections(self) -> None:
        """Clean up stale WebSocket connections."""
        current_time = datetime.now()
        stale_connections = []

        for connection_id, last_activity in self._connection_last_activity.items():
            # Remove connections inactive for more than 30 minutes
            if (current_time - last_activity).seconds > 1800:
                stale_connections.append(connection_id)

        for connection_id in stale_connections:
            self._unregister_connection(connection_id)
            _LOGGER.debug("Cleaned up stale WebSocket connection: %s", connection_id)