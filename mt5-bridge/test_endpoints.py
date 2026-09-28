import os
import urllib.request
import urllib.error
import json
from dotenv import load_dotenv

load_dotenv('c:/Users/boybu/OneDrive/Documents/Projects/Trade-Analysis/mt5-bridge/.env')
token = os.getenv('MT5_BRIDGE_TOKEN')

print("=== 1. Test /health without token ===")
try:
    urllib.request.urlopen('http://127.0.0.1:8001/health')
    print("UNEXPECTED: Got 200 without token")
except urllib.error.HTTPError as e:
    print(f"PASS: Rejected without token with HTTP {e.code}")

print("=== 2. Test /health with token ===")
req = urllib.request.Request('http://127.0.0.1:8001/health', headers={'X-Bridge-Token': token})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print("PASS /health:", json.dumps(data))

print("=== 3. Test /account with token ===")
req = urllib.request.Request('http://127.0.0.1:8001/account', headers={'X-Bridge-Token': token})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print("PASS /account fields:", list(data.keys()))
    print("login:", data.get("login"), "server:", data.get("server"), "currency:", data.get("currency"), "balance:", data.get("balance"), "equity:", data.get("equity"))

print("=== 4. Test /price/EURUSD with token ===")
req = urllib.request.Request('http://127.0.0.1:8001/price/EURUSD', headers={'X-Bridge-Token': token})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print("PASS /price/EURUSD:", data)

print("=== 5. Test /positions with token ===")
req = urllib.request.Request('http://127.0.0.1:8001/positions', headers={'X-Bridge-Token': token})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print(f"PASS /positions count: {len(data)}")
    if data:
        print("First position:", data[0])

print("=== 6. Test /history with token ===")
req = urllib.request.Request('http://127.0.0.1:8001/history?days=30', headers={'X-Bridge-Token': token})
with urllib.request.urlopen(req) as resp:
    data = json.loads(resp.read().decode())
    print(f"PASS /history count: {len(data)}")
    if data:
        print("First trade:", data[0])
