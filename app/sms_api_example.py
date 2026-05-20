import requests

BASE_URL = "http://localhost:5000/api"

def send_sms(token, recipient, message, sender="ALROSY"):
    headers = {"Authorization": f"Bearer {token}"}
    data = {"recipient": recipient, "message": message, "sender": sender}
    response = requests.post(f"{BASE_URL}/send-sms", json=data, headers=headers)
    return response.json()

def send_bulk_sms(token, recipients, message, sender="ALROSY"):
    headers = {"Authorization": f"Bearer {token}"}
    results = []
    for recipient in recipients:
        data = {"recipient": recipient, "message": message, "sender": sender}
        response = requests.post(f"{BASE_URL}/send-sms", json=data, headers=headers)
        results.append(response.json())
    return results

def get_sms_numbers(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/sms-numbers", headers=headers)
    return response.json()

def get_sms_ranges(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/sms-ranges", headers=headers)
    return response.json()

def get_sms_cdr(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/sms-cdr", headers=headers)
    return response.json()

def get_sms_stats(token):
    headers = {"Authorization": f"Bearer {token}"}
    response = requests.get(f"{BASE_URL}/sms-stats", headers=headers)
    return response.json()
