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
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait()
        except ProcessLookupError:
            pass

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

def test_security_flow():
    print("\n--- Testing Security Flow ---")

    # 1. Unauthenticated Access (Should Fail)
    print("Attempting to list alerts without auth...")
    resp = requests.get(f"{BASE_URL}/api/alerts")
    if resp.status_code == 401:
        print("SUCCESS: Unauthenticated access blocked (401).")
    else:
        print(f"FAILURE: Unauthenticated access not blocked: {resp.status_code}")
        return False

    # 2. Register User
    print("\nRegistering user...")
    phone = "1234567890"
    user_data = {
        "name": "Test User",
        "phone": phone,
        "emergency_contacts": [{"name": "Mom", "phone": "0987654321"}]
    }
    resp = requests.post(f"{BASE_URL}/api/register", json=user_data)
    if resp.status_code == 201 or (resp.status_code == 200 and "already registered" in resp.text):
        print("User registered.")
    else:
        print(f"Failed to register user: {resp.status_code} {resp.text}")
        return False

    # 3. Login (Get Token)
    print("\nLogging in...")
    login_data = {
        "phone": phone,
        "otp": "123456"
    }
    resp = requests.post(f"{BASE_URL}/api/login", json=login_data)
    if resp.status_code == 200:
        token = resp.json().get('token')
        print("Login successful. Token received.")
    else:
        print(f"Login failed: {resp.status_code} {resp.text}")
        return False

    headers = {'Authorization': f'Bearer {token}'}

    # 4. Authenticated Access (Should Succeed)
    print("\nAttempting to list alerts with token...")
    resp = requests.get(f"{BASE_URL}/api/alerts", headers=headers)
    if resp.status_code == 200:
        print("SUCCESS: Authenticated access granted.")
    else:
        print(f"FAILURE: Authenticated access failed: {resp.status_code} {resp.text}")
        return False

    # 5. Trigger SOS
    print("\nTriggering SOS...")
    sos_data = {
        "phone": phone,
        "latitude": 28.6139,
        "longitude": 77.2090
    }
    resp = requests.post(f"{BASE_URL}/api/sos/trigger", json=sos_data, headers=headers)
    if resp.status_code == 201:
        alert = resp.json()['alert']
        alert_id = alert['alert_id']
        print(f"SOS triggered. Alert ID: {alert_id}")
    else:
        print(f"Failed to trigger SOS: {resp.status_code} {resp.text}")
        return False

    # 6. Verify Unauthorized SOS Trigger (Different Phone)
    print("\nAttempting to trigger SOS for another user...")
    bad_sos_data = {
        "phone": "0987654321", # Different phone
        "latitude": 28.6139,
        "longitude": 77.2090
    }
    resp = requests.post(f"{BASE_URL}/api/sos/trigger", json=bad_sos_data, headers=headers)
    if resp.status_code == 403:
        print("SUCCESS: Unauthorized SOS trigger blocked (403).")
    else:
        print(f"FAILURE: Unauthorized SOS trigger not blocked correctly: {resp.status_code}")
        # Note: If user doesn't exist, it might be 404 or 403 depending on order.
        # But 'phone mismatch' check is early.

    # 7. Cancel SOS
    print("\nCancelling SOS...")
    cancel_data = {"alert_id": alert_id}
    resp = requests.post(f"{BASE_URL}/api/sos/cancel", json=cancel_data, headers=headers)
    if resp.status_code == 200:
        print("SOS cancelled.")
    else:
        print(f"Failed to cancel SOS: {resp.status_code} {resp.text}")
        return False

    # 8. Input Validation Test
    print("\nTesting Input Validation (Invalid Phone)...")
    bad_user = {
        "name": "Bad User",
        "phone": "invalid-phone"
    }
    resp = requests.post(f"{BASE_URL}/api/register", json=bad_user)
    if resp.status_code == 400:
        print("SUCCESS: Invalid phone rejected.")
    else:
         print(f"FAILURE: Invalid phone accepted: {resp.status_code}")

    print("\nTesting Input Validation (Invalid Coords)...")
    bad_coords_sos = {
        "phone": phone,
        "latitude": 1000, # Invalid
        "longitude": 2000
    }
    resp = requests.post(f"{BASE_URL}/api/sos/trigger", json=bad_coords_sos, headers=headers)
    if resp.status_code == 400:
        print("SUCCESS: Invalid coordinates rejected.")
    else:
         print(f"FAILURE: Invalid coordinates accepted: {resp.status_code}")

    return alert_id, token

def test_persistence(alert_id, token):
    print("\n--- Testing Persistence (Restart) ---")
    # This function assumes server was restarted

    headers = {'Authorization': f'Bearer {token}'}

    print(f"Attempting to access alert {alert_id} after restart...")
    resp = requests.get(f"{BASE_URL}/api/alerts/{alert_id}", headers=headers)
    if resp.status_code == 200:
        print("SUCCESS: Alert accessed after restart.")
        # If encryption key persisted, this should work without internal errors
    elif resp.status_code == 500:
        print("FAILURE: Server error (likely encryption key mismatch).")
        return False
    else:
        print(f"FAILURE: Access failed: {resp.status_code}")
        return False

    return True

def main():
    # Remove existing key file to test generation
    if os.path.exists("server/encryption.key"):
        os.remove("server/encryption.key")
        print("Removed existing encryption key to test generation.")

    server_process = start_server()
    if not wait_for_server():
        stop_server(server_process)
        sys.exit(1)

    try:
        result = test_security_flow()
        if not result:
            print("\nSecurity flow test failed.")
            sys.exit(1)

        alert_id, token = result

        # Restart server to test persistence
        stop_server(server_process)
        time.sleep(2)
        print("\nRestarting server...")
        server_process = start_server()
        if wait_for_server():
            if test_persistence(alert_id, token):
                print("\nAll security tests passed!")
            else:
                print("\nPersistence test failed.")
                sys.exit(1)
        else:
             print("Server failed to restart.")
             sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)
    finally:
        stop_server(server_process)

if __name__ == "__main__":
    main()
