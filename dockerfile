FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

WORKDIR /app

COPY requirements.txt .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# 🔴 هذا هو السطر الأهم: تثبيت المتصفحات الخاصة بـ Playwright
RUN playwright install chromium

COPY . .

CMD ["python", "main.py"]
