import requests
import pandas as pd
from datetime import datetime

BASE_URL = "https://metering.beeline.kz:4443"
AUTH_ENDPOINT = "/api/auth/login"
DEVICE_MESSAGES_ENDPOINT = "/api/device/messages"
DEVICE_LIST_ENDPOINT = "/api/device/metering_devices"
REPORT_FILENAME = "Metering devices.xlsx"


def convert_to_unix(date_str):
    return int(datetime.strptime(date_str, "%d-%m-%Y").timestamp())


def authenticate_manual(email, password):
    headers = {"Content-Type": "application/json", "Accept": "application/json"}
    try:
        response = requests.post(
            BASE_URL + AUTH_ENDPOINT,
            json={"email": email, "password": password, "personal_data_access": True},
            headers=headers,
            timeout=10
        )
        response.raise_for_status()
        auth_data = response.json()
        return auth_data.get("data", {}).get("access_token")
    except:
        return None


def get_all_devices(token):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    try:
        response = requests.post(BASE_URL + DEVICE_LIST_ENDPOINT, headers=headers, json={"paginate": False}, timeout=10)
        response.raise_for_status()
        devices = response.json().get("data", {}).get("metering_devices", [])
        return [device.get("id") for device in devices]
    except:
        return []


def get_device_messages(token, device_id, start_date, stop_date):
    headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
    payload = {
        "device_id": device_id,
        "msgType": 1,
        "msgGroup": 0,
        "startDate": convert_to_unix(start_date),
        "stopDate": convert_to_unix(stop_date),
        "paginate": True,
        "per_page": 50,
        "profile_type": 0,
        "with_transformation_ratio": True,
        "with_loss_factor": True
    }
    try:
        response = requests.post(BASE_URL + DEVICE_MESSAGES_ENDPOINT, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        return response.json().get("data", {}).get("messages", {}).get("data", [])
    except:
        return []


def create_excel_report(all_messages):
    if not all_messages:
        return None
    df = pd.concat(all_messages, ignore_index=True)
    if "datetime_at_hour" not in df.columns:
        df["datetime_at_hour"] = "-"
    df["consumption"] = df.sort_values(by=["device_id", "datetime_at_hour"]).groupby("device_id")["in1"].diff().fillna("-")
    df = df[["device_id", "in1", "rssi", "consumption", "datetime_at_hour"]]
    df.to_excel(REPORT_FILENAME, index=False, sheet_name="Device Messages")
    return REPORT_FILENAME