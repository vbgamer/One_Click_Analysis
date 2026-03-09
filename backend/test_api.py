import requests
import time
import sys

BASE_URL = "http://localhost:8000"

def test_pipeline():
    # 1. Login
    print("LOGGING IN...")
    auth_data = {"username": "final@test.com", "password": "password"}
    try:
        res = requests.post(f"{BASE_URL}/auth/login", data=auth_data)
        if res.status_code != 200:
            print(f"Login failed: {res.text}")
            return
        token = res.json()["access_token"]
        headers = {"Authorization": f"Bearer {token}"}
        print("LOGIN SUCCESS")
        
        # 2. Upload
        print("UPLOADING FILE...")
        files = {'file': ('test_churn.csv', open('test_churn.csv', 'rb'), 'text/csv')}
        res = requests.post(f"{BASE_URL}/upload", headers=headers, files=files)
        if res.status_code != 200:
            print(f"Upload failed: {res.text}")
            return
        
        job_id = res.json()["id"]
        print(f"UPLOAD SUCCESS. Job ID: {job_id}")
        
        # 3. Poll Status
        print("POLLING STATUS...")
        for i in range(20): # Wait up to 100s
            res = requests.get(f"{BASE_URL}/status/{job_id}", headers=headers)
            status = res.json()["status"]
            print(f"Status: {status}")
            
            if status == "done":
                print("PROCESSING COMPLETE!")
                print(f"Report URL: {res.json()['report_url']}")
                return job_id
            elif status == "failed":
                print("PROCESSING FAILED")
                return
            
            time.sleep(5)
            
        print("TIMEOUT WAITING FOR PROCESSING")
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_pipeline()
