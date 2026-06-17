FROM python:3.11-slim

WORKDIR /app

# Cài đặt thêm curl để chạy lệnh HEALTHCHECK không bị sập container
RUN apt-get update && apt-get install -y curl && rm -rf /var/lib/apt/lists/*

RUN useradd -u 8888 appuser && chown -R appuser:appuser /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY src/ ./src

USER appuser

HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

# Đã sửa lỗi: Thêm "--app-dir", "src" để uvicorn tìm đúng thư mục code
CMD ["uvicorn", "iot_app.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000"]