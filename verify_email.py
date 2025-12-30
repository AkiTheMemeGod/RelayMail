import requests
import sys

def verify_email():
    url = "http://localhost:5001/api/v1/send"
    payload = {
        "to": "relaymailingservices@gmail.com",
        "subject": "Test Email from RelayMail",
        "body": "This is a test email sent from the RelayMail backend."
    }
    
    headers = {
        "Authorization": "Bearer FdjhaQyT4_Uhi_Nla1pyk8_o0mdFAWJV2lo4GgiUwGE",
        "Content-Type": "application/json"
    }
    
    try:
        print(f"Sending request to {url}...")
        response = requests.post(url, json=payload, headers=headers)
        
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("SUCCESS: Email sent successfully.")
        else:
            print("FAILURE: Email sending failed.")
            sys.exit(1)
            
    except Exception as e:
        print(f"ERROR: Could not connect to backend. {e}")
        sys.exit(1)

if __name__ == "__main__":
    verify_email()
