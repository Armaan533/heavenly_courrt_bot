import os
import urllib.request
import json
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("TOKEN")
APP_ID = os.getenv("APP_ID")

url = f"https://discord.com/api/v10/applications/{APP_ID}/commands"

data = {
    "name": "launch",
    "description": "Launch the Heavenly Court Visualizer",
    "type": 4,           
    "handler": 2,        
    "integration_types": [0, 1], 
    "contexts": [0, 1, 2] 
}

req = urllib.request.Request(
    url, 
    data=json.dumps(data).encode('utf-8'), 
    headers={
        "Authorization": f"Bot {TOKEN}",
        "Content-Type": "application/json"
    }, 
    method='POST'
)

try:
    with urllib.request.urlopen(req) as response:
        print("✅ SUCCESS! The Launch button was forcibly added to your bot.")
except urllib.error.HTTPError as e:
    error_msg = e.read().decode('utf-8')
    print(f"❌ ERROR: {e.code} - {error_msg}")