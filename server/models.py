"""
Database models for Women's Safety System
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
import enum
import json

Base = declarative_base()


class AlertStatus(enum.Enum):
    """Alert status enumeration"""
    TRIGGERED = "triggered"
    ACKNOWLEDGED = "acknowledged"
    DISPATCHED = "dispatched"
    RESPONDING = "responding"
    RESOLVED = "resolved"
    CANCELLED = "cancelled"
    FALSE_ALARM = "false_alarm"


class ThreatLevel(enum.Enum):
    """Threat level enumeration"""
    CRITICAL = "critical"
    HIGH = "high"
    MODERATE = "moderate"
    LOW = "low"


class User(Base):
    """User model"""
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    ephemeral_id = Column(String(64), unique=True, index=True)  # Rotates every 24h
    name = Column(String(100))
    phone = Column(String(20), unique=True)
    encrypted_phone = Column(String(256))  # Encrypted storage
    emergency_contacts = Column(Text)  # JSON array of contacts
    preferences = Column(Text)  # JSON object with user preferences
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    is_verified = Column(Boolean, default=False)
    trust_score = Column(Float, default=1.0)  # For false alarm tracking
    
    # Relationships
    alerts = relationship("Alert", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User {self.ephemeral_id}>"
    
    def to_dict(self):
        # Helper to format datetime with timezone
        def format_dt(dt):
            if not dt:
                return None
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        
        return {
            'id': self.id,
            'ephemeral_id': self.ephemeral_id,
            'name': self.name,
            'phone': self.phone[-4:].rjust(len(self.phone), '*'),  # Masked phone
            'is_verified': self.is_verified,
            'created_at': format_dt(self.created_at)
        }


class Alert(Base):
    """Alert/SOS model"""
    __tablename__ = 'alerts'
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(String(64), unique=True, index=True)  # UUID
    user_id = Column(Integer, ForeignKey('users.id'))
    
    # Status and classification
    status = Column(Enum(AlertStatus), default=AlertStatus.TRIGGERED)
    threat_level = Column(Enum(ThreatLevel), default=ThreatLevel.MODERATE)
    is_false_alarm = Column(Boolean, default=False)
    
    # Location data (encrypted)
    encrypted_location = Column(Text)  # Encrypted JSON with GPS coordinates
    coarse_location = Column(String(200))  # Human-readable, 500m radius
    latitude = Column(Float)  # For demo/testing only
    longitude = Column(Float)
    accuracy = Column(Float)  # meters
    
    # Trigger information
    trigger_method = Column(String(50))  # button, shake, voice, auto
    trigger_context = Column(Text)  # JSON with accelerometer data, etc.
    
    # Timestamps
    triggered_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    acknowledged_at = Column(DateTime)
    dispatched_at = Column(DateTime)
    resolved_at = Column(DateTime)
    
    # Response information
    response_time_seconds = Column(Integer)
    assigned_responders = Column(Text)  # JSON array of responder IDs
    civilian_responders = Column(Text)  # JSON array
    
    # AI assessment
    ai_risk_score = Column(Float)
    ai_confidence = Column(Float)
    ai_factors = Column(Text)  # JSON with risk factors
    
    # Mesh network tracking
    relay_path = Column(Text)  # JSON array of node IDs
    hops_count = Column(Integer, default=0)
    
    # Media evidence
    has_audio = Column(Boolean, default=False)
    has_video = Column(Boolean, default=False)
    media_urls = Column(Text)  # JSON array
    
    # Privacy and audit
    access_log = Column(Text)  # JSON array of access records
    auto_purge_at = Column(DateTime)
    
    # Relationships
    user = relationship("User", back_populates="alerts")
    location_updates = relationship("LocationUpdate", back_populates="alert", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Alert {self.alert_id} - {self.status.value}>"
    
    def to_dict(self, include_sensitive=False):
        # Helper to format datetime with timezone
        def format_dt(dt):
            if not dt:
                return None
            # Ensure timezone-aware datetime
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt.isoformat()
        
        data = {
            'id': self.id,
            'alert_id': self.alert_id,
            'status': self.status.value,
            'threat_level': self.threat_level.value,
            'trigger_method': self.trigger_method,
            'triggered_at': format_dt(self.triggered_at),
            'acknowledged_at': format_dt(self.acknowledged_at),
            'response_time_seconds': self.response_time_seconds,
            'ai_risk_score': self.ai_risk_score,
            'coarse_location': self.coarse_location
        }
        
        if include_sensitive:
            data.update({
                'latitude': self.latitude,
                'longitude': self.longitude,
                'accuracy': self.accuracy,
                'user': self.user.to_dict() if self.user else None
            })
        
        return data


class LocationUpdate(Base):
    """Real-time location updates during active alert"""
    __tablename__ = 'location_updates'
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey('alerts.id'))
    
    latitude = Column(Float)
    longitude = Column(Float)
    accuracy = Column(Float)
    speed = Column(Float)  # m/s
    heading = Column(Float)  # degrees
    
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Relationships
    alert = relationship("Alert", back_populates="location_updates")
    
    def to_dict(self):
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'accuracy': self.accuracy,
            'speed': self.speed,
            'heading': self.heading,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


class Responder(Base):
    """Responder (police, volunteer) model"""
    __tablename__ = 'responders'
    
    id = Column(Integer, primary_key=True)
    responder_id = Column(String(64), unique=True)
    name = Column(String(100))
    type = Column(String(50))  # police, volunteer, medical
    phone = Column(String(20))
    
    # Location
    latitude = Column(Float)
    longitude = Column(Float)
    coverage_radius = Column(Float, default=1000)  # meters
    
    # Status
    is_available = Column(Boolean, default=True)
    current_alert_id = Column(String(64))
    
    # Stats
    total_responses = Column(Integer, default=0)
    average_response_time = Column(Float)
    rating = Column(Float, default=5.0)
    
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    def to_dict(self):
        return {
            'id': self.id,
            'responder_id': self.responder_id,
            'name': self.name,
            'type': self.type,
            'is_available': self.is_available,
            'rating': self.rating,
            'latitude': self.latitude,
            'longitude': self.longitude
        }


class MeshNode(Base):
    """Mesh network node model"""
    __tablename__ = 'mesh_nodes'
    
    id = Column(Integer, primary_key=True)
    node_id = Column(String(64), unique=True)
    node_type = Column(String(50))  # smart_pole, bus, phone, beacon
    
    latitude = Column(Float)
    longitude = Column(Float)
    
    is_active = Column(Boolean, default=True)
    last_seen = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    # Stats
    messages_relayed = Column(Integer, default=0)
    uptime_percentage = Column(Float, default=100.0)
    
    # Hardware info
    battery_level = Column(Float)
    signal_strength = Column(Float)
    
    def to_dict(self):
        return {
            'node_id': self.node_id,
            'node_type': self.node_type,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'is_active': self.is_active,
            'messages_relayed': self.messages_relayed
        }


class AuditLog(Base):
    """Audit trail for data access"""
    __tablename__ = 'audit_logs'
    
    id = Column(Integer, primary_key=True)
    alert_id = Column(String(64), index=True)
    user_id = Column(Integer)
    
    action = Column(String(100))  # viewed_location, accessed_data, etc.
    actor = Column(String(100))  # who accessed
    actor_role = Column(String(50))  # police, admin, etc.
    
    ip_address = Column(String(50))
    timestamp = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    
    details = Column(Text)  # JSON with additional info
    
    def to_dict(self):
        return {
            'action': self.action,
            'actor': self.actor,
            'actor_role': self.actor_role,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }


# Database initialization
def init_db(db_path='womensafety.db'):
    """Initialize database"""
    engine = create_engine(f'sqlite:///{db_path}')
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get database session"""
    Session = sessionmaker(bind=engine)
    return Session()
