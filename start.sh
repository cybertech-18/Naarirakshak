#!/bin/bash
set -e

echo "🛡️  Starting Women's Safety System"

# Kill any existing process
pkill -f "python.*server/app.py" 2>/dev/null || true

# Wait for port to be free
sleep 2

# Check if port is still in use
if lsof -Pi :8000 -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "⚠️  Port 8000 is still in use. Killing process..."
    kill -9 $(lsof -t -i:8000) 2>/dev/null || true
    sleep 2
fi

# Start server
export FLASK_CONFIG=production
nohup python3 server/app.py > server.log 2>&1 &
echo $! > server.pid

# Wait for server to start
sleep 3

# Check for HTTPS certificates
if [ -f "server/certs/cert.pem" ] && [ -f "server/certs/key.pem" ]; then
    PROTOCOL="https"
    HTTPS_STATUS="🔒 HTTPS Enabled"
else
    PROTOCOL="http"
    HTTPS_STATUS="⚠️  HTTP Mode (Run ./setup_https.sh for HTTPS)"
fi

# Get local IP
LOCAL_IP=$(ipconfig getifaddr en0 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}' || echo "your-local-ip")

# Check if server is running
if curl -k -s ${PROTOCOL}://localhost:8000/api/health > /dev/null 2>&1; then
    echo "✅ Server started successfully!"
    echo ""
    echo "$HTTPS_STATUS"
    echo ""
    echo "🌐 Local Access:"
    echo "   Dashboard: ${PROTOCOL}://localhost:8000"
    echo "   Mobile App: ${PROTOCOL}://localhost:8000/app"
    echo ""
    echo "📱 Mobile/Network Access:"
    echo "   ${PROTOCOL}://${LOCAL_IP}:8000/app"
    echo ""
    if [ "$PROTOCOL" = "http" ]; then
        echo "⚠️  Geolocation may not work on mobile devices with HTTP"
        echo "   Run: ./setup_https.sh to enable HTTPS"
        echo ""
    fi
    echo "📋 View logs: tail -f server.log"
    echo "🛑 Stop server: ./stop.sh"
else
    echo "❌ Server failed to start. Check server.log for details."
    tail -n 20 server.log
    exit 1
fi
