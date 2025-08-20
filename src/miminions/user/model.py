"""
User model definitions for MiMinions

This module provides the core user data models including User, UserProfile,
and UserPreferences classes for managing user information and settings.
"""

import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any, Union
from dataclasses import dataclass, field
from enum import Enum


class UserRole(Enum):
    """User roles for access control"""
    ADMIN = "admin"
    USER = "user"
    GUEST = "guest"
    MODERATOR = "moderator"


class UserStatus(Enum):
    """User account status"""
    ACTIVE = "active"
    INACTIVE = "inactive"
    SUSPENDED = "suspended"
    PENDING = "pending"


@dataclass
class UserPreferences:
    """
    User preferences and settings
    
    Stores user-specific configuration and preferences for the MiMinions system.
    """
    
    # Interface preferences
    theme: str = "default"
    language: str = "en"
    timezone: str = "UTC"
    
    # Notification preferences
    email_notifications: bool = True
    push_notifications: bool = False
    notification_frequency: str = "daily"
    
    # Privacy preferences
    data_sharing: bool = False
    analytics_consent: bool = True
    
    # Agent preferences
    default_agent_name: str = "Assistant"
    max_concurrent_agents: int = 3
    auto_save_workspace: bool = True
    
    # Custom preferences
    custom_settings: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert preferences to dictionary"""
        return {
            "theme": self.theme,
            "language": self.language,
            "timezone": self.timezone,
            "email_notifications": self.email_notifications,
            "push_notifications": self.push_notifications,
            "notification_frequency": self.notification_frequency,
            "data_sharing": self.data_sharing,
            "analytics_consent": self.analytics_consent,
            "default_agent_name": self.default_agent_name,
            "max_concurrent_agents": self.max_concurrent_agents,
            "auto_save_workspace": self.auto_save_workspace,
            "custom_settings": self.custom_settings
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserPreferences':
        """Create preferences from dictionary"""
        return cls(**data)


@dataclass
class UserProfile:
    """
    Extended user profile information
    
    Contains additional user information beyond basic authentication data.
    """
    
    # Personal information
    first_name: str = ""
    last_name: str = ""
    display_name: str = ""
    bio: str = ""
    avatar_url: str = ""
    
    # Contact information
    email: str = ""
    phone: str = ""
    website: str = ""
    
    # Professional information
    company: str = ""
    job_title: str = ""
    department: str = ""
    
    # Social information
    location: str = ""
    timezone: str = "UTC"
    date_of_birth: Optional[datetime] = None
    
    # Metadata
    tags: List[str] = field(default_factory=list)
    interests: List[str] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert profile to dictionary"""
        return {
            "first_name": self.first_name,
            "last_name": self.last_name,
            "display_name": self.display_name,
            "bio": self.bio,
            "avatar_url": self.avatar_url,
            "email": self.email,
            "phone": self.phone,
            "website": self.website,
            "company": self.company,
            "job_title": self.job_title,
            "department": self.department,
            "location": self.location,
            "timezone": self.timezone,
            "date_of_birth": self.date_of_birth.isoformat() if self.date_of_birth else None,
            "tags": self.tags,
            "interests": self.interests,
            "skills": self.skills
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'UserProfile':
        """Create profile from dictionary"""
        # Handle date_of_birth conversion
        if data.get('date_of_birth'):
            data['date_of_birth'] = datetime.fromisoformat(data['date_of_birth'])
        return cls(**data)


@dataclass
class User:
    """
    Core user model for MiMinions
    
    Represents a user in the system with authentication, profile, and preferences.
    """
    
    # Core identification
    user_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    username: str = ""
    
    # Authentication
    email: str = ""
    password_hash: str = ""
    salt: str = ""
    
    # Status and role
    role: UserRole = UserRole.USER
    status: UserStatus = UserStatus.PENDING
    
    # Timestamps
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    last_login: Optional[datetime] = None
    
    # Profile and preferences
    profile: UserProfile = field(default_factory=UserProfile)
    preferences: UserPreferences = field(default_factory=UserPreferences)
    
    # Security
    failed_login_attempts: int = 0
    locked_until: Optional[datetime] = None
    password_changed_at: Optional[datetime] = None
    
    # Session management
    session_tokens: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Post-initialization setup"""
        if not self.username and self.email:
            self.username = self.email.split('@')[0]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert user to dictionary"""
        return {
            "user_id": self.user_id,
            "username": self.username,
            "email": self.email,
            "password_hash": self.password_hash,
            "salt": self.salt,
            "role": self.role.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "profile": self.profile.to_dict(),
            "preferences": self.preferences.to_dict(),
            "failed_login_attempts": self.failed_login_attempts,
            "locked_until": self.locked_until.isoformat() if self.locked_until else None,
            "password_changed_at": self.password_changed_at.isoformat() if self.password_changed_at else None,
            "session_tokens": self.session_tokens
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'User':
        """Create user from dictionary"""
        # Handle enum conversions
        data['role'] = UserRole(data['role'])
        data['status'] = UserStatus(data['status'])
        
        # Handle datetime conversions
        for field in ['created_at', 'updated_at', 'last_login', 'locked_until', 'password_changed_at']:
            if data.get(field):
                data[field] = datetime.fromisoformat(data[field])
        
        # Handle nested objects
        data['profile'] = UserProfile.from_dict(data.get('profile', {}))
        data['preferences'] = UserPreferences.from_dict(data.get('preferences', {}))
        
        return cls(**data)
    
    def update_last_login(self):
        """Update last login timestamp"""
        self.last_login = datetime.utcnow()
        self.updated_at = datetime.utcnow()
    
    def increment_failed_login(self):
        """Increment failed login attempts"""
        self.failed_login_attempts += 1
        self.updated_at = datetime.utcnow()
    
    def reset_failed_login(self):
        """Reset failed login attempts"""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.updated_at = datetime.utcnow()
    
    def is_locked(self) -> bool:
        """Check if user account is locked"""
        if self.locked_until and datetime.utcnow() < self.locked_until:
            return True
        return False
    
    def is_active(self) -> bool:
        """Check if user account is active"""
        return self.status == UserStatus.ACTIVE and not self.is_locked()
    
    def get_full_name(self) -> str:
        """Get user's full name"""
        if self.profile.first_name and self.profile.last_name:
            return f"{self.profile.first_name} {self.profile.last_name}"
        elif self.profile.display_name:
            return self.profile.display_name
        else:
            return self.username
    
    def add_session_token(self, token: str):
        """Add a session token"""
        if token not in self.session_tokens:
            self.session_tokens.append(token)
            self.updated_at = datetime.utcnow()
    
    def remove_session_token(self, token: str):
        """Remove a session token"""
        if token in self.session_tokens:
            self.session_tokens.remove(token)
            self.updated_at = datetime.utcnow()
    
    def clear_session_tokens(self):
        """Clear all session tokens"""
        self.session_tokens.clear()
        self.updated_at = datetime.utcnow()
