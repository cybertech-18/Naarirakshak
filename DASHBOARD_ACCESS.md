# 🛡️ Naarirakshak - Dashboard Access Guide v1.1

## 🌐 Server Information
- **Local Access**: http://localhost:8000
- **Network Access**: http://192.168.1.3:8000
- **Status**: Running on HTTP (HTTPS recommended for mobile geolocation)

---

## 📊 Available Dashboards

### 1. **Control Center Dashboard** 
🔗 **URL**: http://192.168.1.3:8000/ (or `/`)

**Purpose**: Main monitoring dashboard for emergency response teams

**Features**:
- Real-time alert monitoring
- Live map with alert locations
- Responder availability tracking
- Alert management (acknowledge, dispatch, resolve)
- Statistics overview
- WebSocket notifications for new alerts

**Best For**: Control room operators, emergency coordinators

---

### 2. **Mobile App** 
🔗 **URL**: http://192.168.1.3:8000/app

**Purpose**: Mobile interface for users to trigger SOS alerts

**Features**:
- User registration (name + phone)
- SOS emergency button
- Real-time location sharing
- Alert cancellation
- Alert history
- Location sharing with contacts

**Best For**: End users, women seeking safety assistance

**Important**: Works best on HTTPS for geolocation. On mobile browsers, allow location permissions.

---

### 3. **Admin Control Panel** 
🔗 **URL**: http://192.168.1.3:8000/admin

**Purpose**: Administrative dashboard for managing responders and volunteers

**Features**:
- System statistics overview
- Volunteer request management (approve/reject)
- Active responder management
- Add new responders directly
- Remove responders
- Real-time notifications

**Best For**: System administrators, HR managers

**Tabs**:
- 📊 Overview: System stats
- 🙋 Volunteer Requests: Pending applications
- 👮 Active Responders: Current responder list
- ➕ Add Responder: Create new responder accounts

---

### 4. **Responder Dashboard** 
🔗 **URL**: http://192.168.1.3:8000/responder

**Purpose**: Dashboard for emergency responders (police, volunteers, medical)

**Features**:
- Active alert feed
- Response to alerts
- Mark alerts as complete
- Personal statistics
- Google Maps integration
- Real-time alert notifications

**Best For**: Police officers, volunteers, medical teams

**Login Credentials** (Demo):
- **Responder ID**: 1-25 (any number between 1 and 25)
- **Password**: `responder123`

---

## 🔧 API Endpoints

### Health Check
```
GET http://192.168.1.3:8000/api/health
```
Returns server status and statistics

### Register User
```
POST http://192.168.1.3:8000/api/register
Content-Type: application/json

{
  "name": "User Name",
  "phone": "+91 9876543210"
}
```

### Trigger SOS
```
POST http://192.168.1.3:8000/api/sos/trigger
Content-Type: application/json

{
  "phone": "+91 9876543210",
  "latitude": 28.6139,
  "longitude": 77.2090,
  "trigger_method": "button"
}
```

### Get All Alerts
```
GET http://192.168.1.3:8000/api/alerts
GET http://192.168.1.3:8000/api/alerts?status=triggered
```

### Get All Responders
```
GET http://192.168.1.3:8000/api/responders
```

---

## 📱 Mobile Access Instructions

### From Your Phone on the Same WiFi Network:

1. **Ensure your phone is on the same WiFi** as your computer (192.168.1.x network)

2. **Open your mobile browser** (Chrome, Safari, etc.)

3. **Access the dashboards**:
   - Mobile App: `http://192.168.1.3:8000/app`
   - Control Center: `http://192.168.1.3:8000/`
   - Admin Panel: `http://192.168.1.3:8000/admin`
   - Responder: `http://192.168.1.3:8000/responder`

4. **Allow location permissions** when prompted (required for SOS functionality)

5. **Note**: Geolocation works best on HTTPS. On HTTP, some mobile browsers may restrict location access.

---

## 🔒 Enable HTTPS (Recommended for Mobile)

To enable HTTPS for better mobile geolocation support:

```bash
cd /Users/ayush18/womensafety
./setup_https.sh
```

After enabling HTTPS, access URLs will change to:
- `https://192.168.1.3:8000/...`

You'll need to accept the self-signed certificate warning on first access.

---

## 🚀 Quick Start Guide

### For Testing the System:

1. **Start Server** (Already running):
   ```bash
   cd /Users/ayush18/womensafety
   python3 server/app.py
   ```

2. **Open Control Center** on your computer:
   - http://localhost:8000/

3. **Open Mobile App** on your phone:
   - http://192.168.1.3:8000/app
   - Register with name and phone number
   - Try triggering an SOS alert

4. **Watch the Control Center** for real-time updates:
   - Alert appears on map
   - Sound notification plays
   - Browser notification pops up

5. **Open Responder Dashboard** in another tab:
   - http://192.168.1.3:8000/responder
   - Login with ID: 1, Password: responder123
   - Respond to the active alert

6. **Check Admin Panel**:
   - http://192.168.1.3:8000/admin
   - View system statistics
   - Manage responders

---

## 🎯 User Roles & Workflows

### End User (Mobile App)
1. Register → 2. Grant location access → 3. Press SOS if emergency → 4. Wait for help → 5. Cancel when safe

### Control Center Operator
1. Monitor dashboard → 2. Acknowledge new alerts → 3. Dispatch responders → 4. Mark as resolved

### Responder
1. Login → 2. View active alerts → 3. Respond to alert → 4. Navigate to location → 5. Mark complete

### Administrator
1. Review volunteer requests → 2. Approve/reject → 3. Manage responders → 4. Monitor statistics

---

## 🐛 Troubleshooting

### "Geolocation not working on mobile"
- Use HTTPS instead of HTTP (run `./setup_https.sh`)
- Check browser location permissions
- Try on localhost if using Chrome

### "Can't access from phone"
- Ensure phone and computer are on same WiFi
- Check IP address matches (192.168.1.3)
- Disable firewall temporarily to test

### "Server not responding"
- Check if server is running: `ps aux | grep app.py`
- Restart server: `python3 server/app.py`
- Check port 8000 is not in use: `lsof -i :8000`

### "Responder login not working"
- Use demo credentials: ID: 1-25, Password: responder123
- Clear browser cache/cookies

---

## 📞 Support & Documentation

- **GitHub**: cybertech-18/Naarirakshak
- **Branch**: v1.1
- **Database**: SQLite (womensafety.db in server directory)
- **Demo Data**: 25 responders auto-generated on first run

---

## 🔄 Server Control

**Start Server**:
```bash
cd /Users/ayush18/womensafety
python3 server/app.py
```

**Stop Server**:
```bash
# Press Ctrl+C in the terminal
# Or from another terminal:
pkill -f "python3 server/app.py"
```

**Check Status**:
```bash
curl http://localhost:8000/api/health
```

---

## ✨ Key Features Overview

- ✅ Real-time WebSocket communication
- ✅ Geolocation tracking with live updates
- ✅ AI-powered threat assessment
- ✅ Multi-responder coordination
- ✅ Encrypted location data
- ✅ Alert history and audit logs
- ✅ Volunteer management system
- ✅ Responsive mobile interface
- ✅ Browser notifications and sound alerts
- ✅ Admin panel for system management

---

**Last Updated**: November 24, 2025
**Version**: 1.1
**Status**: ✅ All systems operational
