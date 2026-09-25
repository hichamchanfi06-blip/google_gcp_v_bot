# استخدام صورة بايثون الرسمية مع أدوات playwright
FROM mcr.microsoft.com/playwright/python:v1.45.0-jammy

# تعيين دليل العمل
WORKDIR /program

# نسخ ملفات المشروع
COPY requirements.txt .
COPY main.py .

# تثبيت مكتبات بايثون
RUN pip install --no-cache-dir -r requirements.txt

# تثبيت متصفح Chromium فقط (لتقليل الحجم)
RUN playwright install chromium

# أمر التشغيل
CMD ["python", "main.py"]
