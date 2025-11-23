"""
Configuration settings for Women's Safety System
"""
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    
    # Server settings
    HOST = '0.0.0.0'
    PORT = 8000
    DEBUG = False
    
    # Security
    SECRET_KEY = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')
    ENCRYPTION_ENABLED = True
    SESSION_TIMEOUT = 3600  # seconds
    
    # Database
    DATABASE_PATH = 'womensafety.db'
    SQLALCHEMY_DATABASE_URI = f'sqlite:///{DATABASE_PATH}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Features
    MESH_NETWORK_ENABLED = True
    AI_THREAT_ASSESSMENT = True
    AUTO_PURGE_HOURS = 48
    LOCATION_UPDATE_INTERVAL = 10  # seconds
    
    # Alert settings
    CRITICAL_RESPONSE_TIME = 300  # 5 minutes
    ALERT_RADIUS_METERS = 100  # for civilian responders
    MAX_CIVILIAN_RESPONDERS = 5
    
    # Privacy settings
    INITIAL_LOCATION_RADIUS = 500  # meters, coarse location
    PRECISE_LOCATION_AUTH_REQUIRED = True
    DATA_RETENTION_DAYS = 2
    AUDIT_LOG_RETENTION_DAYS = 90
    
    # Mesh network
    MESH_TTL = 300  # seconds
    MESH_MAX_HOPS = 10
    MESH_RELAY_PRIORITY = ['recent', 'critical', 'unacknowledged']
    
    # AI/ML
    THREAT_LEVEL_THRESHOLD = 0.7
    FALSE_ALARM_THRESHOLD = 0.3
    MODEL_UPDATE_INTERVAL = 86400  # 24 hours
    
    # Response coordination
    ENABLE_CIVILIAN_RESPONDERS = True
    ENABLE_AUTOMATED_DISPATCH = True
    ENABLE_CCTV_TRIGGER = True
    ENABLE_SMART_LIGHTING = True
    
    # API rate limiting
    RATE_LIMIT_ENABLED = True
    MAX_REQUESTS_PER_MINUTE = 60
    
    # WebSocket
    WEBSOCKET_PING_TIMEOUT = 60
    WEBSOCKET_PING_INTERVAL = 25
    
    # Logging
    LOG_LEVEL = 'INFO'
    LOG_FILE = 'server.log'
    
    # External integrations
    MAPS_API_KEY = os.environ.get('MAPS_API_KEY', '')
    SMS_GATEWAY_API = os.environ.get('SMS_GATEWAY_API', '')
    EMAIL_ENABLED = False
    
    # Testing
    DEMO_MODE = True  # Enable simulation features
    MOCK_GPS = True
    MOCK_RESPONDERS = True


class ProductionConfig(Config):
    """Production configuration"""
    PORT = 8000
    DEBUG = False
    DEMO_MODE = False
    MOCK_GPS = False
    MOCK_RESPONDERS = False
    

class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    DEMO_MODE = True


config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': DevelopmentConfig
}
