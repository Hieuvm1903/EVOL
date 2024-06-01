import requests

# Replace 'YOUR_API_KEY' with your actual API key
API_KEY = 'eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1bmlxdWVfbmFtZSI6IjEiLCJyb2xlIjoiYWRtaW4iLCJuYmYiOjE3MDE4NDQyNDQsImV4cCI6MTcwMjQ0OTA0NCwiaWF0IjoxNzAxODQ0MjQ0fQ.4Hiq-XQveZim-g9X0jM8-fxzgl_6AxDGMIpJu4pVuSY'
API_ENDPOINT = 'https://localhost:7189/api/Villa'

headers = {
    'Authorization': f'Bearer {API_KEY}',
    'Content-Type': 'application/json'
}

response = requests.get(API_ENDPOINT, headers=headers)

if response.status_code == 200:
    data = response.json()
    # Process the retrieved data
    print(data)
else:
    print(f"Error: {response.status_code} - {response.text}")