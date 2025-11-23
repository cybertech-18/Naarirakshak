"""
AI-powered threat assessment and false alarm detection
"""
import numpy as np
from datetime import datetime, time, timedelta, timezone
from typing import Dict, Any, Tuple
import json


class ThreatAssessmentEngine:
    """AI engine for analyzing alert severity and detecting false alarms"""
    
    def __init__(self):
        """Initialize threat assessment engine"""
        # Risk factors and weights (simplified model for demo)
        self.time_weights = self._initialize_time_weights()
        self.location_risk_zones = {}  # Will be populated with historical data
        self.user_patterns = {}  # User behavior patterns
        
    def _initialize_time_weights(self) -> Dict[int, float]:
        """Initialize time-based risk weights (hour of day)"""
        weights = {}
        for hour in range(24):
            if 0 <= hour < 6:  # Late night/early morning
                weights[hour] = 1.5
            elif 6 <= hour < 9:  # Morning
                weights[hour] = 0.7
            elif 9 <= hour < 17:  # Daytime
                weights[hour] = 0.8
            elif 17 <= hour < 21:  # Evening
                weights[hour] = 1.0
            else:  # Night
                weights[hour] = 1.3
        return weights
    
    def assess_threat_level(self, alert_data: Dict[str, Any]) -> Tuple[str, float, Dict[str, Any]]:
        """
        Assess threat level based on multiple factors
        
        Args:
            alert_data: Dictionary containing alert information
                - latitude, longitude
                - trigger_method
                - time
                - user_history
                - accelerometer_data (optional)
                
        Returns:
            Tuple of (threat_level, confidence_score, risk_factors)
        """
        risk_score = 0.0
        risk_factors = {}
        
        # Time-based risk
        current_time = datetime.now(timezone.utc)
        hour = current_time.hour
        time_risk = self.time_weights.get(hour, 1.0)
        risk_score += time_risk * 0.3
        risk_factors['time_risk'] = time_risk
        
        # Trigger method analysis
        trigger_method = alert_data.get('trigger_method', 'button')
        trigger_risk = self._analyze_trigger_method(trigger_method, alert_data)
        risk_score += trigger_risk * 0.25
        risk_factors['trigger_risk'] = trigger_risk
        
        # Location-based risk
        latitude = alert_data.get('latitude')
        longitude = alert_data.get('longitude')
        location_risk = self._analyze_location_risk(latitude, longitude)
        risk_score += location_risk * 0.25
        risk_factors['location_risk'] = location_risk
        
        # User behavior pattern
        user_id = alert_data.get('user_id')
        pattern_risk = self._analyze_user_pattern(user_id, latitude, longitude, current_time)
        risk_score += pattern_risk * 0.2
        risk_factors['pattern_risk'] = pattern_risk
        
        # Normalize risk score (0-1)
        risk_score = min(risk_score, 1.0)
        
        # Determine threat level
        if risk_score >= 0.8:
            threat_level = 'critical'
            confidence = 0.9
        elif risk_score >= 0.6:
            threat_level = 'high'
            confidence = 0.8
        elif risk_score >= 0.4:
            threat_level = 'moderate'
            confidence = 0.7
        else:
            threat_level = 'low'
            confidence = 0.6
        
        risk_factors['overall_risk_score'] = risk_score
        risk_factors['assessment_time'] = current_time.isoformat()
        
        return threat_level, confidence, risk_factors
    
    def _analyze_trigger_method(self, method: str, alert_data: Dict[str, Any]) -> float:
        """
        Analyze risk based on trigger method
        
        Args:
            method: Trigger method (button, shake, voice, auto)
            alert_data: Additional alert data
            
        Returns:
            Risk score (0-1)
        """
        method_scores = {
            'button': 0.7,  # Standard trigger
            'shake': 0.8,   # Indicates movement/struggle
            'voice': 0.9,   # Voice activation suggests urgency
            'auto': 0.95,   # Auto-triggered by pattern detection
            'proximity': 0.85  # Following pattern detected
        }
        
        base_score = method_scores.get(method, 0.7)
        
        # Check for accelerometer data indicating struggle
        if 'accelerometer_data' in alert_data:
            accel = alert_data['accelerometer_data']
            if self._detect_struggle_pattern(accel):
                base_score = min(base_score + 0.2, 1.0)
        
        return base_score
    
    def _detect_struggle_pattern(self, accelerometer_data: Dict[str, Any]) -> bool:
        """
        Detect struggle pattern from accelerometer data
        
        Args:
            accelerometer_data: Dict with x, y, z acceleration values
            
        Returns:
            True if struggle pattern detected
        """
        try:
            # Simplified pattern detection (in production, use trained ML model)
            values = accelerometer_data.get('values', [])
            if len(values) < 10:
                return False
            
            # Calculate variance and peaks
            arr = np.array(values)
            variance = np.var(arr)
            
            # High variance indicates rapid movement
            return variance > 50  # Threshold for demo
        except:
            return False
    
    def _analyze_location_risk(self, latitude: float, longitude: float) -> float:
        """
        Analyze risk based on location
        
        Args:
            latitude: GPS latitude
            longitude: GPS longitude
            
        Returns:
            Risk score (0-1)
        """
        if latitude is None or longitude is None:
            return 0.5  # Default moderate risk
        
        # Check against known risk zones
        location_key = f"{latitude:.3f},{longitude:.3f}"
        
        if location_key in self.location_risk_zones:
            return self.location_risk_zones[location_key]
        
        # In demo, use simple heuristic
        # In production, use historical crime data and ML models
        
        # Example: Areas far from city center might be riskier
        # This is just for demo - replace with real data
        city_center = (28.6139, 77.2090)  # Delhi coords for example
        distance = self._calculate_distance(
            latitude, longitude,
            city_center[0], city_center[1]
        )
        
        # Simplified risk calculation
        if distance < 5:  # Within 5km of center
            return 0.6
        elif distance < 15:
            return 0.7
        else:
            return 0.8
    
    def _calculate_distance(self, lat1: float, lon1: float, 
                           lat2: float, lon2: float) -> float:
        """
        Calculate distance between two GPS coordinates (km)
        
        Args:
            lat1, lon1: First coordinate
            lat2, lon2: Second coordinate
            
        Returns:
            Distance in kilometers
        """
        from math import radians, sin, cos, sqrt, atan2
        
        R = 6371  # Earth radius in km
        
        lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        
        a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
        c = 2 * atan2(sqrt(a), sqrt(1-a))
        
        return R * c
    
    def _analyze_user_pattern(self, user_id: int, latitude: float, 
                             longitude: float, current_time: datetime) -> float:
        """
        Analyze if alert matches user's normal patterns
        
        Args:
            user_id: User identifier
            latitude, longitude: Current location
            current_time: Current timestamp
            
        Returns:
            Risk score (0-1), higher if unusual
        """
        if user_id not in self.user_patterns:
            return 0.5  # No pattern data, moderate risk
        
        user_pattern = self.user_patterns[user_id]
        
        # Check if location is unusual
        usual_locations = user_pattern.get('usual_locations', [])
        is_usual_location = any(
            self._calculate_distance(latitude, longitude, loc['lat'], loc['lng']) < 1
            for loc in usual_locations
        )
        
        # Check if time is unusual
        hour = current_time.hour
        usual_hours = user_pattern.get('usual_active_hours', [])
        is_usual_time = hour in usual_hours
        
        # Calculate risk
        risk = 0.5
        if not is_usual_location:
            risk += 0.2
        if not is_usual_time:
            risk += 0.2
        
        return min(risk, 1.0)
    
    def detect_false_alarm(self, alert_data: Dict[str, Any], 
                          user_history: Dict[str, Any]) -> Tuple[bool, float]:
        """
        Detect potential false alarm
        
        Args:
            alert_data: Current alert data
            user_history: User's alert history
            
        Returns:
            Tuple of (is_false_alarm, confidence)
        """
        false_alarm_score = 0.0
        
        # Check user's false alarm history
        false_alarm_rate = user_history.get('false_alarm_rate', 0.0)
        if false_alarm_rate > 0.3:  # More than 30% false alarms
            false_alarm_score += 0.3
        
        # Check trigger method
        trigger_method = alert_data.get('trigger_method')
        if trigger_method == 'button':
            # Button press could be accidental
            false_alarm_score += 0.2
        
        # Check cancellation time
        # If user cancels immediately, likely accidental
        # This would be checked after a delay in real implementation
        
        # Check context
        if alert_data.get('context', {}).get('screen_locked', False):
            # If screen was locked, less likely accidental
            false_alarm_score -= 0.2
        
        false_alarm_score = max(0.0, min(false_alarm_score, 1.0))
        
        is_false_alarm = false_alarm_score > 0.5
        confidence = abs(false_alarm_score - 0.5) * 2  # 0-1 scale
        
        return is_false_alarm, confidence
    
    def update_location_risk(self, latitude: float, longitude: float, 
                            incident_occurred: bool):
        """
        Update location risk database based on incident outcomes
        
        Args:
            latitude: GPS latitude
            longitude: GPS longitude
            incident_occurred: True if real incident, False if false alarm
        """
        location_key = f"{latitude:.3f},{longitude:.3f}"
        
        current_risk = self.location_risk_zones.get(location_key, 0.5)
        
        # Update risk score using exponential moving average
        alpha = 0.3  # Learning rate
        new_risk = current_risk * (1 - alpha) + (1.0 if incident_occurred else 0.2) * alpha
        
        self.location_risk_zones[location_key] = new_risk
    
    def update_user_pattern(self, user_id: int, latitude: float, 
                           longitude: float, timestamp: datetime):
        """
        Update user's behavior pattern
        
        Args:
            user_id: User identifier
            latitude, longitude: User location
            timestamp: Activity timestamp
        """
        if user_id not in self.user_patterns:
            self.user_patterns[user_id] = {
                'usual_locations': [],
                'usual_active_hours': set()
            }
        
        pattern = self.user_patterns[user_id]
        
        # Add to usual hours
        pattern['usual_active_hours'].add(timestamp.hour)
        
        # Add location if not already present
        location = {'lat': latitude, 'lng': longitude}
        is_new_location = all(
            self._calculate_distance(latitude, longitude, loc['lat'], loc['lng']) > 0.5
            for loc in pattern['usual_locations']
        )
        
        if is_new_location:
            pattern['usual_locations'].append(location)
            
            # Keep only last 10 usual locations
            if len(pattern['usual_locations']) > 10:
                pattern['usual_locations'] = pattern['usual_locations'][-10:]


# Global threat assessment engine instance
_threat_engine = None


def get_threat_engine() -> ThreatAssessmentEngine:
    """Get global threat assessment engine instance"""
    global _threat_engine
    if _threat_engine is None:
        _threat_engine = ThreatAssessmentEngine()
    return _threat_engine
