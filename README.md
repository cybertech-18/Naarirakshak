# Naarirakshak

## Women's Safety System - v1.1

A comprehensive real-time safety monitoring and emergency response system with AI-powered threat detection, mesh networking, and privacy-first design.

### Version 1.1 Features (New!)

- **Responder Dashboard**: Dedicated interface for emergency responders to view and respond to alerts
- **Admin Control Panel**: Manage volunteer registrations, approve responders, and monitor system statistics
- **Volunteer Registration System**: Allow citizens to apply to become safety volunteers
- **Custom Notification System**: In-app notifications replacing browser notifications for better UX
- **Enhanced UI**: Modern, gradient-based design with improved animations and user experience
- **Better Alert Management**: Responders can mark alerts as complete, track response times

### Core Features

- Real-time emergency alert system
- Live location tracking and mapping
- AI-powered threat assessment
- Privacy-first architecture with data encryption
- Mesh network simulation for offline capability
- Multi-responder coordination
- Control center dashboard for monitoring
- Mobile PWA for users

### System Components

1. **Mobile App** (`/app`) - User-facing PWA for triggering alerts
2. **Control Center** (`/`) - Real-time monitoring dashboard for authorities
3. **Responder Dashboard** (`/responder`) - Interface for emergency responders
4. **Admin Panel** (`/admin`) - System administration and volunteer management

### Technology Stack

- **Backend**: Python/Flask with SocketIO
- **Frontend**: HTML5, CSS3, JavaScript
- **Database**: SQLite with SQLAlchemy ORM
- **Real-time**: WebSocket communication
- **Maps**: Leaflet.js for geospatial visualization
- **AI**: Custom threat detection engine
- **Encryption**: AES-256 for sensitive data

### Installation

```bash
# Install dependencies
pip install -r server/requirements.txt

# Initialize database
python -c "from server.models import init_db; init_db()"

# Run server
python server/app.py
```

### Development Setup

```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r server/requirements.txt

# Run in development mode
export FLASK_ENV=development
python server/app.py
```

### Public Access (via ngrok)

```bash
# Install ngrok
brew install ngrok

# Authenticate
ngrok config add-authtoken YOUR_TOKEN

# Start tunnel
ngrok http 8000
```

### API Endpoints

#### v1.0 Endpoints
- `POST /api/alert/trigger` - Trigger emergency alert
- `GET /api/alerts/active` - Get active alerts
- `GET /api/responders` - Get available responders
- `POST /api/responders` - Register new responder

#### v1.1 Endpoints (New!)
- `GET /api/admin/stats` - Admin dashboard statistics
- `GET /api/admin/volunteers/pending` - Pending volunteer applications
- `POST /api/admin/volunteer/approve` - Approve volunteer
- `POST /api/admin/volunteer/reject` - Reject volunteer
- `POST /api/admin/responder/add` - Add responder (admin)
- `POST /api/admin/responder/remove` - Remove responder
- `GET /api/responder/:id` - Get responder details
- `GET /api/responder/:id/stats` - Responder statistics
- `POST /api/alert/respond` - Respond to alert
- `POST /api/alert/complete` - Mark alert complete
- `POST /api/volunteer/register` - Register as volunteer

### Version History

#### v1.1 (Current)
- Added responder dashboard with real-time alerts
- Implemented admin control panel
- Created volunteer registration system
- Custom in-app notification system
- Major UI improvements across all interfaces
- Enhanced alert tracking and response management

#### v1.0
- Initial release with basic alert system
- Control center dashboard
- Mobile PWA
- Real-time WebSocket communication
- AI threat detection
- 25 demo responders

### Security Features

- End-to-end encryption for location data
- Ephemeral user IDs (rotating every 24h)
- Privacy-first data retention policies
- Audit logging for all data access
- Masked phone numbers in UI

### Contributing

This is a demo/prototype system. For production deployment:

1. Implement proper authentication
2. Use production-grade database (PostgreSQL)
3. Add SSL certificates
4. Implement rate limiting
5. Add comprehensive logging
6. Set up monitoring and alerts

### License

MIT License - See LICENSE file for details

### Contact

For questions or support, please open an issue on GitHub.

---

**Note**: This is a prototype system for demonstration purposes. Production deployment requires additional security hardening and compliance with local regulations.
