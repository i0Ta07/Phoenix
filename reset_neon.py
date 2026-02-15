import requests,os

NEON_API_KEY = os.getenv("NEON_API_KEY")
NEON_PROJECT_ID = os.getenv("NEON_PROJECT_ID")
PROD_BRANCH_ID = os.getenv("PROD_BRANCH_ID")
BASE_BRANCH_ID = os.getenv("BASE_BRANCH_ID")

url = f"https://console.neon.tech/api/v2/projects/{NEON_PROJECT_ID}/branches/{PROD_BRANCH_ID}/reset"

headers = {
    "Authorization": f"Bearer {NEON_API_KEY}",
    "Content-Type": "application/json"
}

payload = {
    "source_branch_id": BASE_BRANCH_ID
}

response = requests.post(url, headers=headers, json=payload)
print(response.status_code, response.json())
response.raise_for_status()