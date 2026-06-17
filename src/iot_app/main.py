from fastapi import FastAPI, HTTPException, Security, Depends, status
from fastapi.security import APIKeyHeader
import os

app = FastAPI()

# --- Phần cấu hình Auth cũ chúng ta đã sửa ---
API_KEY_NAME = "X-API-Token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=False)
EXPECTED_TOKEN = os.getenv("API_TOKEN", "secret_token")

def verify_token(token: str = Depends(api_key_header)):
    if not token or token != EXPECTED_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized access - Invalid or missing token"
        )
    return token

# --- SỬA LẠI HÀM HEALTH CHO ĐÚNG SCHEMA CỦA BÀI LAB ---
@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "iot-ingestion",
        "version": "0.4.0"
    }

# --- KIỂM TRA LẠI CÁC ROUTE BỊ LỖI 404 NẾU CÓ ---
# Đảm bảo các hàm xử lý dữ liệu IoT phía dưới của bạn đang được định nghĩa ĐÚNG CHÍNH TẢ là "/readings" (có chữ s).
# Ví dụ:
# @app.post("/readings", dependencies=[Depends(verify_token)])
# def create_reading(...):
#     ...
#
# @app.get("/readings/latest")
# def get_latest_readings(...):
#     ...