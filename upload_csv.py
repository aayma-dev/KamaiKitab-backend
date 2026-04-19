import requests

url = "http://localhost:8000/api/earnings/import-csv"
token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ0ZXN0QGV4YW1wbGUuY29tIiwidXNlcl9pZCI6MywiZXhwIjoxNzc2NTQ0NjkwLCJ0eXBlIjoiYWNjZXNzIiwiaWF0IjoxNzc2NTQyODkwfQ.YbzEEbndYw8vPiNcpsQmt-D-uXTaroR2Jd_sXcGC4dY"

with open("test_earnings.csv", "rb") as f:
    files = {"file": ("test_earnings.csv", f, "text/csv")}
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.post(url, headers=headers, files=files)

print(f"Status: {response.status_code}")
print(f"Response: {response.json()}")
