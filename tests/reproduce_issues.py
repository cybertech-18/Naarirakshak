import requests
import time
import subprocess
import os
import signal
import sys
import json

SERVER_PORT = 8000
BASE_URL = f"http://localhost:{SERVER_PORT}"

def start_server():
    print("Starting server...")
    # Using specific python executable
    process = subprocess.Popen(
        [sys.executable, "server/app.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        preexec_fn=os.setsid
    )
    return process

def stop_server(process):
    print("Stopping server...")
    if process:
        os.killpg(os.getpgid(process.pid), signal.SIGTERM)
        process.wait()

def wait_for_server():
    for _ in range(30):
        try:
            response = requests.get(f"{BASE_URL}/api/health")
            if response.status_code == 200:
                print("Server is ready.")
                return True
        except requests.ConnectionError:
            pass
        time.sleep(1)
    print("Server failed to start.")
    return False

def test_unauthenticated_access():
    print("\n--- Testing Unauthenticated Access ---")

    # 1. Register User
    print("Registering user...")
    user_data = {
        "name": "Test User",
        "phone": "1234567890",
        "emergency_contacts": [{"name": "Mom", "phone": "0987654321"}]
    }
    resp = requests.post(f"{BASE_URL}/api/register", json=user_data)
    if resp.status_code == 201:
        print("User registered.")
    else:
        print(f"Failed to register user: {resp.status_code} {resp.text}")
        return

    # 2. Trigger SOS
    print("Triggering SOS...")
    sos_data = {
        "phone": "1234567890",
        "latitude": 28.6139,
        "longitude": 77.2090
    }
    resp = requests.post(f"{BASE_URL}/api/sos/trigger", json=sos_data)
    if resp.status_code == 201:
        alert = resp.json()['alert']
        alert_id = alert['alert_id']
        print(f"SOS triggered. Alert ID: {alert_id}")
    else:
        print(f"Failed to trigger SOS: {resp.status_code} {resp.text}")
        return

    # 3. Access Sensitive Data (Get Alert) without Auth
    print(f"Attempting to access alert {alert_id} without auth...")
    resp = requests.get(f"{BASE_URL}/api/alerts/{alert_id}")
    if resp.status_code == 200:
        data = resp.json()
        print("SUCCESS: Accessed alert details without authentication!")
        print(f"Location: {data.get('latitude')}, {data.get('longitude')}")
    else:
        print(f"Failed to access alert: {resp.status_code}")

    # 4. Get All Alerts without Auth
    print("Attempting to list all alerts without auth...")
    resp = requests.get(f"{BASE_URL}/api/alerts")
    if resp.status_code == 200:
        alerts = resp.json()['alerts']
        print(f"SUCCESS: Listed {len(alerts)} alerts without authentication!")
    else:
        print(f"Failed to list alerts: {resp.status_code}")

    return alert_id

def test_encryption_persistence(alert_id):
    print("\n--- Testing Encryption Persistence ---")
    print("Restarting server...")
    # Server process is managed outside this function in main
    return

def main():
    # Install dependencies if needed (assuming they are installed)

    server_process = start_server()
    if not wait_for_server():
        stop_server(server_process)
        sys.exit(1)

    try:
        alert_id = test_unauthenticated_access()

        if alert_id:
            # Restart server to test persistence
            stop_server(server_process)
            time.sleep(2)
            server_process = start_server()
            if wait_for_server():
                print(f"Attempting to access alert {alert_id} after restart...")
                resp = requests.get(f"{BASE_URL}/api/alerts/{alert_id}")
                if resp.status_code == 200:
                    print("SUCCESS: Alert accessed after restart.")
                    # Check if location is present (decryption worked?)
                    data = resp.json()
                    # If encryption key changed, decrypting location might fail or return garbage?
                    # The server code 'get_alert' calls 'to_dict(include_sensitive=True)' which returns latitude/longitude from DB columns directly.
                    # Wait, 'latitude' and 'longitude' are stored as Float columns in Alert model.
                    # 'encrypted_location' is also stored.
                    # Let's check 'encrypted_location'.
                    # Actually, the 'Alert' model stores plain 'latitude' and 'longitude' for demo/testing!
                    # "latitude = Column(Float)  # For demo/testing only"
                    # So even if encryption fails, the plain text data is leaking.
                    # But let's check if the encryption manager works.
                    # The 'encrypted_location' column stores encrypted JSON.
                    # There is no endpoint to get decrypted 'encrypted_location' explicitly, but 'to_dict' might use it?
                    # No, 'to_dict' uses self.latitude.

                    # However, User phone number is encrypted?
                    # "encrypted_phone = Column(String(256))"
                    # But 'phone' is also stored as plain text "phone = Column(String(20), unique=True)"

                    print("Note: The current implementation stores plain text data alongside encrypted data for demo purposes, so immediate decryption failure might not be obvious via API.")
                    print("However, the EncryptionManager generates a random key on startup, so any data strictly relying on it would be lost.")
                elif resp.status_code == 500:
                     print("FAILURE: Server error accessing alert (likely decryption failure due to key rotation).")
                else:
                    print(f"Response: {resp.status_code}")

    except Exception as e:
        print(f"Error: {e}")
    finally:
        stop_server(server_process)

if __name__ == "__main__":
    main()
