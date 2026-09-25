# استخدام صورة Playwright الرسمية
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

# تعيين دليل العمل
WORKDIR /app

# نسخ ملف المتطلبات
COPY requirements.txt .

# تثبيت المكتبات
RUN pip install --no-cache-dir -r requirements.txt

# تثبيت متصفح Chromium
RUN playwright install chromium

# نسخ باقي الملفات
COPY . .

# تشغيل البوت
CMD ["python", "main.py"]
