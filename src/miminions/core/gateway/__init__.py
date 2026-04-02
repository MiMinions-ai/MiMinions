"""
Gateway — Persistent server runtime for MiMinions.

Provides event-driven architecture, uniform channel abstraction,
session-scoped conversation state, cron scheduling, and startup
orchestration.
"""

# Events (DTOs)
from .events import InboundMessage, OutboundMessage

# Message Bus
from .bus import MessageBus

# Channel Abstraction
from .channel import BaseChannel, ChannelManager

# Session State
from .session import Session, SessionManager, SessionMessage

# Cron Service
from .services import (
    CronJob,
    CronJobState,
    CronPayload,
    CronSchedule,
    CronService,
    CronStore,
)

# Orchestration
from .orchestrator import GatewayOrchestrator, Lifecycle, Phase

__all__ = [
    # Events
    "InboundMessage",
    "OutboundMessage",
    # Bus
    "MessageBus",
    # Channel
    "BaseChannel",
    "ChannelManager",
    # Session
    "Session",
    "SessionManager",
    "SessionMessage",
    # Cron
    "CronJob",
    "CronJobState",
    "CronPayload",
    "CronSchedule",
    "CronService",
    "CronStore",
    # Orchestration
    "GatewayOrchestrator",
    "Lifecycle",
    "Phase",
]
