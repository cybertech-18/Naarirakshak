"""
Women's Safety System - Main Server Application
"""
from flask import Flask, request, jsonify, render_template, send_from_directory
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_cors import CORS
from datetime import datetime, timedelta, timezone
import uuid
import json
import os

# Import local modules
from config import config
from models import (
    init_db, get_session, User, Alert, LocationUpdate, 
    Responder, MeshNode, AuditLog, AlertStatus, ThreatLevel,
    VolunteerRequest, AlertResponse
)
from encryption import get_encryption_manager
from ai_engine import get_threat_engine
from mesh_network import MeshNetworkSimulator

# Initialize Flask app
app = Flask(__name__)
config_name = os.getenv('FLASK_CONFIG', 'development')
app.config.from_object(config[config_name])

# Enable CORS
CORS(app, resources={r"/api/*": {"origins": "*"}})

# Initialize SocketIO
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading')

# Initialize database
engine = init_db(app.config['DATABASE_PATH'])

# Initialize managers
encryption_mgr = get_encryption_manager()
threat_engine = get_threat_engine()
mesh_network = MeshNetworkSimulator()

# Track active connections
active_users = {}  # {user_id: socket_id}
active_alerts = {}  # {alert_id: alert_data}


# ============ REST API ENDPOINTS ============

@app.route('/')
def index():
    """Serve dashboard"""
    return render_template('dashboard.html')


@app.route('/app')
def mobile_app():
    """Serve mobile app for real devices"""
    return render_template('mobile.html')


@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'active_alerts': len(active_alerts),
        'connected_users': len(active_users)
    })


@app.route('/api/register', methods=['POST', 'OPTIONS'])
def register_user():
    """Register new user"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        name = data.get('name')
        phone = data.get('phone')
        
        if not name or not phone:
            return jsonify({'error': 'Name and phone required'}), 400
        
        session = get_session(engine)
        
        # Check if user exists
        existing_user = session.query(User).filter_by(phone=phone).first()
        if existing_user:
            user_dict = existing_user.to_dict()
            # Add full phone for client-side storage
            user_dict['phone_full'] = phone
            return jsonify({
                'message': 'User already registered',
                'user': user_dict
            })
        
        # Create new user
        ephemeral_id = encryption_mgr.generate_ephemeral_id(hash(phone))
        
        user = User(
            ephemeral_id=ephemeral_id,
            name=name,
            phone=phone,
            emergency_contacts=json.dumps(data.get('emergency_contacts', [])),
            preferences=json.dumps(data.get('preferences', {})),
            is_verified=True  # Auto-verify for demo
        )
        
        session.add(user)
        session.commit()
        
        user_dict = user.to_dict()
        # Add full phone for client-side storage (needed for SOS)
        user_dict['phone_full'] = phone
        session.close()
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user_dict
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sos/trigger', methods=['POST', 'OPTIONS'])
def trigger_sos():
    """Trigger SOS alert"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        phone = data.get('phone')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        trigger_method = data.get('trigger_method', 'button')
        
        if not phone:
            return jsonify({'error': 'Phone number required'}), 400
        
        session = get_session(engine)
        
        # Find user
        user = session.query(User).filter_by(phone=phone).first()
        if not user:
            session.close()
            return jsonify({'error': 'User not found'}), 404
        
        # Generate alert ID
        alert_id = str(uuid.uuid4())
        
        # Encrypt location
        encrypted_loc = None
        if latitude and longitude:
            encrypted_loc = encryption_mgr.encrypt_location(latitude, longitude)
        
        # AI threat assessment
        alert_data = {
            'latitude': latitude,
            'longitude': longitude,
            'trigger_method': trigger_method,
            'user_id': user.id,
            'accelerometer_data': data.get('accelerometer_data')
        }
        threat_level, confidence, risk_factors = threat_engine.assess_threat_level(alert_data)
        
        # Create alert
        alert = Alert(
            alert_id=alert_id,
            user_id=user.id,
            status=AlertStatus.TRIGGERED,
            threat_level=ThreatLevel[threat_level.upper()],
            encrypted_location=json.dumps(encrypted_loc) if encrypted_loc else None,
            latitude=latitude,
            longitude=longitude,
            trigger_method=trigger_method,
            trigger_context=json.dumps(data.get('context', {})),
            ai_risk_score=risk_factors.get('overall_risk_score'),
            ai_confidence=confidence,
            ai_factors=json.dumps(risk_factors),
            auto_purge_at=datetime.now(timezone.utc) + timedelta(hours=app.config['AUTO_PURGE_HOURS'])
        )
        
        session.add(alert)
        session.commit()
        
        alert_dict = alert.to_dict(include_sensitive=True)
        alert_dict['user'] = user.to_dict()
        
        # Store in active alerts
        active_alerts[alert_id] = alert_dict
        
        # Broadcast to connected control centers
        socketio.emit('alert_triggered', alert_dict, namespace='/')
        
        # Simulate mesh network propagation
        if app.config['MESH_NETWORK_ENABLED']:
            mesh_network.propagate_alert(alert_dict)
        
        # Find nearby responders
        nearby_responders = find_nearby_responders(session, latitude, longitude)
        
        session.close()
        
        return jsonify({
            'message': 'SOS alert triggered',
            'alert': alert_dict,
            'nearby_responders': [r.to_dict() for r in nearby_responders]
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/sos/cancel', methods=['POST', 'OPTIONS'])
def cancel_sos():
    """Cancel active SOS alert"""
    if request.method == 'OPTIONS':
        return '', 204
    
    try:
        data = request.json
        alert_id = data.get('alert_id')
        verification = data.get('verification', '')
        
        if not alert_id:
            return jsonify({'error': 'Alert ID required'}), 400
        
        session = get_session(engine)
        
        # Find alert
        alert = session.query(Alert).filter_by(alert_id=alert_id).first()
        if not alert:
            session.close()
            return jsonify({'error': 'Alert not found'}), 404
        
        # Update status
        alert.status = AlertStatus.CANCELLED
        alert.resolved_at = datetime.now(timezone.utc)
        
        # Make triggered_at timezone-aware if it's naive
        triggered_at = alert.triggered_at
        if triggered_at.tzinfo is None:
            triggered_at = triggered_at.replace(tzinfo=timezone.utc)
        
        alert.response_time_seconds = int(
            (alert.resolved_at - triggered_at).total_seconds()
        )
        
        session.commit()
        
        # Remove from active alerts
        if alert_id in active_alerts:
            del active_alerts[alert_id]
        
        # Broadcast cancellation
        socketio.emit('alert_cancelled', {
            'alert_id': alert_id,
            'cancelled_at': alert.resolved_at.isoformat()
        }, namespace='/')
        
        session.close()
        
        return jsonify({
            'message': 'Alert cancelled',
            'alert_id': alert_id
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts', methods=['GET'])
def get_alerts():
    """Get all alerts"""
    try:
        session = get_session(engine)
        
        # Query parameters
        status = request.args.get('status')
        limit = int(request.args.get('limit', 50))
        
        query = session.query(Alert)
        
        if status:
            query = query.filter_by(status=AlertStatus[status.upper()])
        
        alerts = query.order_by(Alert.triggered_at.desc()).limit(limit).all()
        
        alerts_data = [alert.to_dict(include_sensitive=True) for alert in alerts]
        
        session.close()
        
        return jsonify({
            'alerts': alerts_data,
            'count': len(alerts_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/<alert_id>', methods=['GET'])
def get_alert(alert_id):
    """Get specific alert details"""
    try:
        session = get_session(engine)
        
        alert = session.query(Alert).filter_by(alert_id=alert_id).first()
        if not alert:
            session.close()
            return jsonify({'error': 'Alert not found'}), 404
        
        alert_dict = alert.to_dict(include_sensitive=True)
        alert_dict['user'] = alert.user.to_dict() if alert.user else None
        
        # Get location updates
        updates = session.query(LocationUpdate).filter_by(
            alert_id=alert.id
        ).order_by(LocationUpdate.timestamp.desc()).all()
        
        alert_dict['location_updates'] = [u.to_dict() for u in updates]
        
        # Log access
        audit_log = AuditLog(
            alert_id=alert_id,
            action='viewed_alert',
            actor='system',
            actor_role='admin',
            ip_address=request.remote_addr
        )
        session.add(audit_log)
        session.commit()
        
        session.close()
        
        return jsonify(alert_dict)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/responders', methods=['GET', 'POST', 'OPTIONS'])
def manage_responders():
    """Get or add responders"""
    if request.method == 'OPTIONS':
        return '', 204
    
    if request.method == 'POST':
        # Add new responder
        try:
            data = request.json
            name = data.get('name')
            responder_type = data.get('type')  # police, medical, volunteer
            phone = data.get('phone')
            latitude = data.get('latitude')
            longitude = data.get('longitude')
            
            if not name or not responder_type or not phone:
                return jsonify({'error': 'Name, type, and phone are required'}), 400
            
            session = get_session(engine)
            
            # Check if responder exists
            existing = session.query(Responder).filter_by(phone=phone).first()
            if existing:
                session.close()
                return jsonify({
                    'message': 'Responder already registered',
                    'responder': existing.to_dict()
                })
            
            # Create new responder
            responder = Responder(
                responder_id=f'R{str(uuid.uuid4())[:8]}',
                name=name,
                type=responder_type,
                phone=phone,
                latitude=latitude,
                longitude=longitude,
                is_available=True,
                rating=5.0
            )
            
            session.add(responder)
            session.commit()
            
            responder_dict = responder.to_dict()
            session.close()
            
            return jsonify({
                'message': 'Responder registered successfully',
                'responder': responder_dict
            }), 201
            
        except Exception as e:
            return jsonify({'error': str(e)}), 500
    
    # GET - Get available responders
    try:
        session = get_session(engine)
        
        responders = session.query(Responder).filter_by(
            is_available=True
        ).all()
        
        responders_data = [r.to_dict() for r in responders]
        
        session.close()
        
        return jsonify({
            'responders': responders_data,
            'count': len(responders_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/mesh/nodes', methods=['GET'])
def get_mesh_nodes():
    """Get mesh network nodes"""
    try:
        session = get_session(engine)
        
        nodes = session.query(MeshNode).filter_by(is_active=True).all()
        nodes_data = [n.to_dict() for n in nodes]
        
        session.close()
        
        return jsonify({
            'nodes': nodes_data,
            'count': len(nodes_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ v1.1 NEW ENDPOINTS ============

@app.route('/admin')
def admin_panel():
    """Serve admin control panel"""
    return render_template('admin.html')


@app.route('/responder')
def responder_dashboard():
    """Serve responder dashboard"""
    return render_template('responder.html')


@app.route('/api/admin/stats', methods=['GET'])
def get_admin_stats():
    """Get admin dashboard statistics"""
    try:
        session = get_session(engine)
        
        total_responders = session.query(Responder).count()
        pending_volunteers = session.query(VolunteerRequest).filter_by(status='pending').count()
        active_alerts = session.query(Alert).filter(
            Alert.status.in_([AlertStatus.TRIGGERED, AlertStatus.ACKNOWLEDGED, AlertStatus.DISPATCHED])
        ).count()
        
        # Today's responses
        today = datetime.now(timezone.utc).date()
        today_responses = session.query(AlertResponse).filter(
            AlertResponse.responded_at >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
        ).count()
        
        session.close()
        
        return jsonify({
            'total_responders': total_responders,
            'pending_volunteers': pending_volunteers,
            'active_alerts': active_alerts,
            'today_responses': today_responses
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/volunteers/pending', methods=['GET'])
def get_pending_volunteers():
    """Get pending volunteer applications"""
    try:
        session = get_session(engine)
        
        volunteers = session.query(VolunteerRequest).filter_by(status='pending').all()
        volunteers_data = [v.to_dict() for v in volunteers]
        
        session.close()
        
        return jsonify(volunteers_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/volunteer/approve', methods=['POST'])
def approve_volunteer():
    """Approve volunteer and convert to responder"""
    try:
        data = request.json
        volunteer_id = data.get('volunteer_id')
        
        session = get_session(engine)
        
        volunteer = session.query(VolunteerRequest).filter_by(id=volunteer_id).first()
        if not volunteer:
            session.close()
            return jsonify({'error': 'Volunteer not found'}), 404
        
        # Create responder from volunteer
        responder = Responder(
            responder_id=f'V{str(uuid.uuid4())[:8]}',
            name=volunteer.name,
            type='Volunteer',
            phone=volunteer.phone,
            latitude=28.6139 + (hash(volunteer.name) % 100) / 10000,  # Random near Delhi
            longitude=77.2090 + (hash(volunteer.name) % 100) / 10000,
            is_available=True,
            rating=5.0
        )
        
        session.add(responder)
        
        # Update volunteer status
        volunteer.status = 'approved'
        volunteer.reviewed_at = datetime.now(timezone.utc)
        volunteer.reviewed_by = 'admin'
        
        session.commit()
        session.close()
        
        # Notify via WebSocket
        socketio.emit('volunteer_approved', {
            'volunteer_id': volunteer_id,
            'name': volunteer.name
        }, namespace='/')
        
        return jsonify({'success': True, 'message': 'Volunteer approved'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/volunteer/reject', methods=['POST'])
def reject_volunteer():
    """Reject volunteer application"""
    try:
        data = request.json
        volunteer_id = data.get('volunteer_id')
        
        session = get_session(engine)
        
        volunteer = session.query(VolunteerRequest).filter_by(id=volunteer_id).first()
        if not volunteer:
            session.close()
            return jsonify({'error': 'Volunteer not found'}), 404
        
        volunteer.status = 'rejected'
        volunteer.reviewed_at = datetime.now(timezone.utc)
        volunteer.reviewed_by = 'admin'
        
        session.commit()
        session.close()
        
        return jsonify({'success': True, 'message': 'Volunteer rejected'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/responder/add', methods=['POST'])
def admin_add_responder():
    """Admin adds new responder directly"""
    try:
        data = request.json
        
        session = get_session(engine)
        
        responder = Responder(
            responder_id=f'R{str(uuid.uuid4())[:8]}',
            name=data['name'],
            type=data['type'],
            phone=data.get('phone', ''),
            latitude=28.6139 + (hash(data['name']) % 100) / 10000,
            longitude=77.2090 + (hash(data['name']) % 100) / 10000,
            is_available=True,
            rating=5.0
        )
        
        session.add(responder)
        session.commit()
        session.close()
        
        return jsonify({'success': True, 'message': 'Responder added'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/responder/remove', methods=['POST'])
def admin_remove_responder():
    """Admin removes a responder"""
    try:
        data = request.json
        responder_id = data.get('responder_id')
        
        session = get_session(engine)
        
        responder = session.query(Responder).filter_by(id=responder_id).first()
        if responder:
            session.delete(responder)
            session.commit()
        
        session.close()
        
        return jsonify({'success': True, 'message': 'Responder removed'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/responder/<int:responder_id>', methods=['GET'])
def get_responder(responder_id):
    """Get responder details"""
    try:
        session = get_session(engine)
        
        responder = session.query(Responder).filter_by(id=responder_id).first()
        if not responder:
            session.close()
            return jsonify({'error': 'Responder not found'}), 404
        
        data = responder.to_dict()
        session.close()
        
        return jsonify(data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/responder/<int:responder_id>/stats', methods=['GET'])
def get_responder_stats(responder_id):
    """Get responder statistics"""
    try:
        session = get_session(engine)
        
        responder = session.query(Responder).filter_by(id=responder_id).first()
        if not responder:
            session.close()
            return jsonify({'error': 'Responder not found'}), 404
        
        total_responses = session.query(AlertResponse).filter_by(responder_id=responder_id).count()
        
        # Today's completions
        today = datetime.now(timezone.utc).date()
        completed_today = session.query(AlertResponse).filter(
            AlertResponse.responder_id == responder_id,
            AlertResponse.status == 'completed',
            AlertResponse.completed_at >= datetime.combine(today, datetime.min.time()).replace(tzinfo=timezone.utc)
        ).count()
        
        session.close()
        
        return jsonify({
            'total_responses': total_responses,
            'completed_today': completed_today,
            'avg_response_time': '5 min'  # Placeholder
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alerts/active', methods=['GET'])
def get_active_alerts():
    """Get all active alerts for responders"""
    try:
        session = get_session(engine)
        
        alerts = session.query(Alert).filter(
            Alert.status.in_([AlertStatus.TRIGGERED, AlertStatus.ACKNOWLEDGED, AlertStatus.DISPATCHED])
        ).all()
        
        alerts_data = []
        for alert in alerts:
            alert_dict = alert.to_dict(include_sensitive=True)
            if alert.user:
                alert_dict['user_name'] = alert.user.name
                alert_dict['phone'] = alert.user.phone
            alerts_data.append(alert_dict)
        
        session.close()
        
        return jsonify(alerts_data)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alert/respond', methods=['POST'])
def respond_to_alert():
    """Responder responds to an alert"""
    try:
        data = request.json
        alert_id = data.get('alert_id')
        responder_id = data.get('responder_id')
        
        session = get_session(engine)
        
        # Create response record
        response = AlertResponse(
            alert_id=alert_id,
            responder_id=responder_id,
            status='responding'
        )
        
        session.add(response)
        
        # Update alert status
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if alert:
            alert.status = AlertStatus.DISPATCHED
        
        # Update responder availability
        responder = session.query(Responder).filter_by(id=responder_id).first()
        if responder:
            responder.is_available = False
            responder.total_responses += 1
        
        session.commit()
        session.close()
        
        # Notify via WebSocket
        socketio.emit('responder_assigned', {
            'alert_id': alert_id,
            'responder_id': responder_id
        }, namespace='/')
        
        return jsonify({'success': True, 'message': 'Response recorded'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/alert/complete', methods=['POST'])
def complete_alert():
    """Mark alert as complete"""
    try:
        data = request.json
        alert_id = data.get('alert_id')
        responder_id = data.get('responder_id')
        
        session = get_session(engine)
        
        # Update response
        response = session.query(AlertResponse).filter_by(
            alert_id=alert_id,
            responder_id=responder_id
        ).first()
        
        if response:
            response.status = 'completed'
            response.completed_at = datetime.now(timezone.utc)
        
        # Update alert
        alert = session.query(Alert).filter_by(id=alert_id).first()
        if alert:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = datetime.now(timezone.utc)
        
        # Update responder
        responder = session.query(Responder).filter_by(id=responder_id).first()
        if responder:
            responder.is_available = True
        
        session.commit()
        session.close()
        
        # Notify via WebSocket
        socketio.emit('alert_resolved', {
            'alert_id': alert_id
        }, namespace='/')
        
        return jsonify({'success': True, 'message': 'Alert completed'})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/volunteer/register', methods=['POST'])
def register_volunteer():
    """User registers to become a volunteer"""
    try:
        data = request.json
        
        session = get_session(engine)
        
        # Check if already registered
        existing = session.query(VolunteerRequest).filter_by(phone=data['phone']).first()
        if existing:
            session.close()
            return jsonify({'error': 'Already registered', 'status': existing.status})
        
        volunteer = VolunteerRequest(
            name=data['name'],
            phone=data['phone'],
            location=data.get('location', ''),
            status='pending'
        )
        
        session.add(volunteer)
        session.commit()
        
        volunteer_data = volunteer.to_dict()
        session.close()
        
        # Notify admin via WebSocket
        socketio.emit('new_volunteer', volunteer_data, namespace='/')
        
        return jsonify({
            'success': True,
            'message': 'Application submitted',
            'volunteer': volunteer_data
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/responder/register', methods=['POST'])
def register_responder():
    """New responder self-registration"""
    try:
        data = request.json
        name = data.get('name')
        phone = data.get('phone')
        password = data.get('password')
        responder_type = data.get('type', 'volunteer')
        location = data.get('location', '')
        
        if not name or not phone or not password:
            return jsonify({'error': 'Name, phone, and password required'}), 400
        
        session = get_session(engine)
        
        # Check if phone already exists
        existing = session.query(Responder).filter_by(phone=phone).first()
        if existing:
            session.close()
            return jsonify({'error': 'Phone number already registered'}), 400
        
        # Create responder
        responder = Responder(
            responder_id=f'R{str(uuid.uuid4())[:8]}',
            name=name,
            type=responder_type,
            phone=phone,
            password=password,  # In production, hash this!
            latitude=28.6139 + (hash(phone) % 100) / 10000,
            longitude=77.2090 + (hash(phone) % 100) / 10000,
            is_available=True,
            rating=5.0
        )
        
        session.add(responder)
        session.commit()
        
        responder_dict = responder.to_dict()
        session.close()
        
        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'responder': responder_dict
        }), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/responder/login', methods=['POST'])
def responder_login():
    """Responder login with phone and password"""
    try:
        data = request.json
        phone = data.get('phone')
        password = data.get('password')
        
        if not phone or not password:
            return jsonify({'error': 'Phone and password required'}), 400
        
        session = get_session(engine)
        
        # For demo: accept responder ID 1-25 with password "responder123"
        if password == 'responder123':
            try:
                responder_id = int(phone)
                if 1 <= responder_id <= 25:
                    responder = session.query(Responder).filter_by(id=responder_id).first()
                    if responder:
                        session.close()
                        return jsonify({
                            'success': True,
                            'responder': responder.to_dict()
                        })
            except:
                pass
        
        # Check phone and password
        responder = session.query(Responder).filter_by(phone=phone).first()
        if not responder or (hasattr(responder, 'password') and responder.password != password):
            session.close()
            return jsonify({'error': 'Invalid credentials'}), 401
        
        session.close()
        
        return jsonify({
            'success': True,
            'responder': responder.to_dict()
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/responder/<int:responder_id>/toggle-status', methods=['POST'])
def toggle_responder_status(responder_id):
    """Toggle responder active/inactive status"""
    try:
        session = get_session(engine)
        
        responder = session.query(Responder).filter_by(id=responder_id).first()
        if not responder:
            session.close()
            return jsonify({'error': 'Responder not found'}), 404
        
        # Toggle availability
        responder.is_available = not responder.is_available
        
        session.commit()
        
        new_status = 'active' if responder.is_available else 'inactive'
        session.close()
        
        # Notify via WebSocket
        socketio.emit('responder_status_changed', {
            'responder_id': responder_id,
            'is_available': responder.is_available
        }, namespace='/')
        
        return jsonify({
            'success': True,
            'is_available': responder.is_available,
            'message': f'Status changed to {new_status}'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/responder/logout', methods=['POST'])
def responder_logout():
    """Logout responder and set status to inactive"""
    try:
        data = request.json
        responder_id = data.get('responder_id')
        
        if not responder_id:
            return jsonify({'error': 'Responder ID required'}), 400
        
        session = get_session(engine)
        
        # Get responder
        responder = session.query(Responder).filter_by(id=responder_id).first()
        
        if not responder:
            session.close()
            return jsonify({'error': 'Responder not found'}), 404
        
        # Set status to inactive
        responder.is_available = False
        session.commit()
        
        session.close()
        
        # Notify via WebSocket
        socketio.emit('responder_logged_out', {
            'responder_id': responder_id,
            'timestamp': datetime.now(timezone.utc).isoformat()
        }, namespace='/')
        
        return jsonify({
            'success': True,
            'message': 'Logged out successfully'
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/admin/responders/all', methods=['GET'])
def get_all_responders_admin():
    """Get all responders (active and inactive) for admin"""
    try:
        session = get_session(engine)
        
        responders = session.query(Responder).all()
        responders_data = [r.to_dict() for r in responders]
        
        session.close()
        
        return jsonify({
            'responders': responders_data,
            'count': len(responders_data)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# ============ WebSocket EVENTS ============

@socketio.on('connect')
def handle_connect():
    """Handle client connection"""
    print(f'Client connected: {request.sid}')
    emit('connected', {'message': 'Connected to control center'})


@socketio.on('disconnect')
def handle_disconnect():
    """Handle client disconnection"""
    print(f'Client disconnected: {request.sid}')
    
    # Remove from active users
    for user_id, socket_id in list(active_users.items()):
        if socket_id == request.sid:
            del active_users[user_id]
            break


@socketio.on('user_register')
def handle_user_register(data):
    """Register user for WebSocket communication"""
    user_id = data.get('user_id')
    if user_id:
        active_users[user_id] = request.sid
        join_room(f'user_{user_id}')
        emit('registered', {'user_id': user_id})


@socketio.on('location_update')
def handle_location_update(data):
    """Handle real-time location updates"""
    try:
        alert_id = data.get('alert_id')
        latitude = data.get('latitude')
        longitude = data.get('longitude')
        
        if not alert_id:
            return
        
        session = get_session(engine)
        
        alert = session.query(Alert).filter_by(alert_id=alert_id).first()
        if not alert:
            session.close()
            return
        
        # Create location update
        location_update = LocationUpdate(
            alert_id=alert.id,
            latitude=latitude,
            longitude=longitude,
            accuracy=data.get('accuracy'),
            speed=data.get('speed'),
            heading=data.get('heading')
        )
        
        session.add(location_update)
        session.commit()
        
        # Broadcast to control centers
        emit('location_updated', {
            'alert_id': alert_id,
            'latitude': latitude,
            'longitude': longitude,
            'timestamp': location_update.timestamp.isoformat()
        }, namespace='/')
        
        session.close()
        
    except Exception as e:
        print(f'Error handling location update: {e}')


@socketio.on('dispatch_responder')
def handle_dispatch_responder(data):
    """Dispatch responder to alert"""
    try:
        alert_id = data.get('alert_id')
        responder_id = data.get('responder_id')
        
        session = get_session(engine)
        
        alert = session.query(Alert).filter_by(alert_id=alert_id).first()
        responder = session.query(Responder).filter_by(
            responder_id=responder_id
        ).first()
        
        if alert and responder:
            alert.status = AlertStatus.DISPATCHED
            alert.dispatched_at = datetime.now(timezone.utc)
            
            # Update assigned responders
            assigned = json.loads(alert.assigned_responders or '[]')
            assigned.append(responder_id)
            alert.assigned_responders = json.dumps(assigned)
            
            # Update responder status
            responder.is_available = False
            responder.current_alert_id = alert_id
            
            session.commit()
            
            # Notify user
            if alert.user_id in active_users:
                emit('responder_dispatched', {
                    'alert_id': alert_id,
                    'responder': responder.to_dict()
                }, room=f'user_{alert.user_id}')
            
            # Broadcast to control centers
            emit('alert_status_changed', {
                'alert_id': alert_id,
                'status': 'dispatched',
                'responder': responder.to_dict()
            }, namespace='/')
        
        session.close()
        
    except Exception as e:
        print(f'Error dispatching responder: {e}')


@socketio.on('update_alert_status')
def handle_update_alert_status(data):
    """Update alert status"""
    try:
        alert_id = data.get('alert_id')
        new_status = data.get('status')
        
        session = get_session(engine)
        
        alert = session.query(Alert).filter_by(alert_id=alert_id).first()
        if alert:
            alert.status = AlertStatus[new_status.upper()]
            
            if new_status == 'resolved':
                alert.resolved_at = datetime.now(timezone.utc)
                
                # Make triggered_at timezone-aware if it's naive
                triggered_at = alert.triggered_at
                if triggered_at.tzinfo is None:
                    triggered_at = triggered_at.replace(tzinfo=timezone.utc)
                
                alert.response_time_seconds = int(
                    (alert.resolved_at - triggered_at).total_seconds()
                )
            
            session.commit()
            
            # Broadcast status change
            socketio.emit('alert_status_changed', {
                'alert_id': alert_id,
                'status': new_status,
                'timestamp': datetime.now(timezone.utc).isoformat()
            }, namespace='/')
        
        session.close()
        
    except Exception as e:
        print(f'Error updating alert status: {e}')


# ============ HELPER FUNCTIONS ============

def find_nearby_responders(session, latitude, longitude, radius_km=5):
    """Find responders within radius"""
    if not latitude or not longitude:
        return []
    
    responders = session.query(Responder).filter_by(is_available=True).all()
    
    nearby = []
    for responder in responders:
        if responder.latitude and responder.longitude:
            distance = calculate_distance(
                latitude, longitude,
                responder.latitude, responder.longitude
            )
            if distance <= radius_km:
                nearby.append(responder)
    
    return nearby


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance between two points (km)"""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


# ============ INITIALIZATION ============

def init_demo_data():
    """Initialize demo data for testing"""
    session = get_session(engine)
    
    # Check if demo data already exists
    existing_responders = session.query(Responder).count()
    if existing_responders > 0:
        session.close()
        return
    
    # Indian names and locations
    responder_names = [
        ('Officer Rajesh Kumar', 'police', '+91-9876543210'),
        ('Officer Priya Sharma', 'police', '+91-9876543211'),
        ('Officer Amit Singh', 'police', '+91-9876543212'),
        ('Officer Kavita Desai', 'police', '+91-9876543213'),
        ('Officer Rahul Verma', 'police', '+91-9876543214'),
        ('Volunteer Anjali Patel', 'volunteer', '+91-9876543215'),
        ('Volunteer Rohan Gupta', 'volunteer', '+91-9876543216'),
        ('Volunteer Neha Reddy', 'volunteer', '+91-9876543217'),
        ('Volunteer Arjun Nair', 'volunteer', '+91-9876543218'),
        ('Volunteer Simran Kaur', 'volunteer', '+91-9876543219'),
        ('Volunteer Vikram Rao', 'volunteer', '+91-9876543220'),
        ('Volunteer Pooja Joshi', 'volunteer', '+91-9876543221'),
        ('Ambulance Unit 1', 'medical', '+91-9876543222'),
        ('Ambulance Unit 2', 'medical', '+91-9876543223'),
        ('Ambulance Unit 3', 'medical', '+91-9876543224'),
        ('Security Team Alpha', 'security', '+91-9876543225'),
        ('Security Team Beta', 'security', '+91-9876543226'),
        ('Community Helper Ravi', 'volunteer', '+91-9876543227'),
        ('Community Helper Meera', 'volunteer', '+91-9876543228'),
        ('Rapid Response Unit 1', 'police', '+91-9876543229'),
        ('Rapid Response Unit 2', 'police', '+91-9876543230'),
        ('Night Patrol Team', 'police', '+91-9876543231'),
        ('Women Safety Squad', 'police', '+91-9876543232'),
        ('Emergency Response Team', 'medical', '+91-9876543233'),
        ('Crisis Support Unit', 'volunteer', '+91-9876543234'),
    ]
    
    # Generate responders with varying locations around Delhi
    responders = []
    base_lat = 28.6139
    base_lon = 77.2090
    
    for i, (name, resp_type, phone) in enumerate(responder_names):
        # Spread responders in a 5km radius
        lat_offset = (i % 5 - 2) * 0.01  # ~1km per 0.01 degree
        lon_offset = ((i // 5) % 5 - 2) * 0.01
        
        responder = Responder(
            responder_id=f'R{str(uuid.uuid4())[:8]}',
            name=name,
            type=resp_type,
            phone=phone,
            latitude=base_lat + lat_offset,
            longitude=base_lon + lon_offset,
            is_available=True
        )
        responders.append(responder)
    
    for responder in responders:
        session.add(responder)
    
    # Add demo mesh nodes
    nodes = [
        MeshNode(
            node_id=f'N{str(uuid.uuid4())[:8]}',
            node_type='smart_pole',
            latitude=28.6139,
            longitude=77.2090,
            is_active=True
        ),
        MeshNode(
            node_id=f'N{str(uuid.uuid4())[:8]}',
            node_type='bus',
            latitude=28.6149,
            longitude=77.2100,
            is_active=True
        )
    ]
    
    for node in nodes:
        session.add(node)
    
    session.commit()
    session.close()
    
    print(f'Demo data initialized: {len(responders)} responders added')



# ============ MAIN ============

if __name__ == '__main__':
    # Initialize demo data
    init_demo_data()
    
    port = app.config['PORT']
    
    # Check for SSL certificates (handle both project root and server dir execution)
    base_path = os.path.dirname(os.path.abspath(__file__))
    ssl_cert = os.path.join(base_path, 'certs', 'cert.pem')
    ssl_key = os.path.join(base_path, 'certs', 'key.pem')
    use_ssl = os.path.exists(ssl_cert) and os.path.exists(ssl_key)
    
    # Get local IP for mobile access
    import socket
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except:
        local_ip = "your-local-ip"
    
    protocol = "https" if use_ssl else "http"
    
    print(f"""
    ╔═══════════════════════════════════════════════════╗
    ║   🛡️  Naarirakshak - Women's Safety System        ║
    ║                      v1.1                         ║
    ║                                                   ║
    ║   🌐 Server Running:                              ║
    ║      Local:   {protocol}://localhost:{port}               ║
    ║      Network: {protocol}://{local_ip}:{port}         ║
    ║                                                   ║
    ║   {'🔒 HTTPS Enabled (Geolocation works!)' if use_ssl else '⚠️  HTTP Mode (Geolocation may not work)'}          ║
    ║   {'   Accept certificate warning on first access' if use_ssl else '   Run ./setup_https.sh to enable HTTPS'}       ║
    ║                                                   ║
    ║   📊 Available Dashboards:                        ║
    ║      • Control Center:  {protocol}://{local_ip}:{port}/          ║
    ║      • Mobile App:      {protocol}://{local_ip}:{port}/app      ║
    ║      • Admin Panel:     {protocol}://{local_ip}:{port}/admin    ║
    ║      • Responder:       {protocol}://{local_ip}:{port}/responder║
    ║                                                   ║
    ║   🔧 API Endpoints:                               ║
    ║      • Health Check:    {protocol}://{local_ip}:{port}/api/health║
    ║      • Register User:   POST /api/register        ║
    ║      • Trigger SOS:     POST /api/sos/trigger     ║
    ║                                                   ║
    ║   💡 Access from mobile: Use network URL above    ║
    ║   ⚡ Press Ctrl+C to stop the server              ║
    ╚═══════════════════════════════════════════════════╝
    """)
    
    # Run server with SSL if available
    if use_ssl:
        print("🔐 Starting HTTPS server...")
        socketio.run(
            app,
            host=app.config['HOST'],
            port=port,
            debug=False,
            use_reloader=False,
            ssl_context=(ssl_cert, ssl_key),
            allow_unsafe_werkzeug=True
        )
    else:
        print("🌐 Starting HTTP server...")
        socketio.run(
            app,
            host=app.config['HOST'],
            port=port,
            debug=False,
            use_reloader=False,
            allow_unsafe_werkzeug=True
        )
