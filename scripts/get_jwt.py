import os
import requests
from dotenv import load_dotenv

load_dotenv()

SECRET = os.getenv("FINAM_TOKEN")
if not SECRET:
    raise RuntimeError("FINAM_TOKEN not set")

url = "https://api.finam.ru/api/v1/auth"
headers = {
    "X-Api-Key": SECRET,
}

resp = requests.post(url, headers=headers)
resp.raise_for_status()

data = resp.json()
jwt = data.get("token")

if not jwt:
    raise RuntimeError("JWT not received")

print("\nJWT:\n")
print(jwt)