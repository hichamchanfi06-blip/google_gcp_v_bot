import asyncio
import logging
import os
import io
import json
import sys
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

# ==========================================
# الإعدادات المطلوبة (تم تعديلها)
# ==========================================
TELEGRAM_TOKEN = "8591926496:AAEjLJPFAz8L1IJn8Kj5187zitAZh2885nc"
CONTAINER_IMAGE = "dx02/aio_v2ray"
ADMIN_ID = 8660614620  # معرف المالك

USER_COOKIES = {}

# دالة للتحقق مما إذا كان المستخدم هو المالك
def is_admin(user_id):
    return user_id == ADMIN_ID

async def send_status(update, text):
    try:
        await update.message.reply_text(f"⏳ {text}")
        logger.info(text)
    except Exception as e:
        logger.error(f"Status Error: {e}")

async def send_screenshot(update, page, caption):
    try:
        screenshot_bytes = await page.screenshot(full_page=False)
        await update.message.reply_photo(photo=io.BytesIO(screenshot_bytes), caption=caption)
    except Exception as e:
        logger.error(f"Screenshot Error: {e}")

async def deploy_on_gcp(update, url, container_image, user_id):
    async with async_playwright() as p:
        try:
            await send_status(update, "جاري تشغيل المتصفح وبدء عملية النشر...")
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
            )

            # إعداد السياق
            context = await browser.new_context(
                user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36',
                viewport={'width': 1280, 'height': 800}
            )

            # تحميل الكوكيز إذا كانت متاحة
            if user_id in USER_COOKIES:
                await context.add_cookies(USER_COOKIES[user_id])
                await send_status(update, "🍪 تم تحميل الكوكيز بنجاح.")

            page = await context.new_page()

            # إعداد stealth
            stealth_applier = Stealth()
            await stealth_applier.apply_stealth_async(page)

            page.set_default_timeout(90000)

            await send_status(update, "🌐 جاري فتح الرابط...")
            await page.goto(url, wait_until='networkidle', timeout=90000)
            await asyncio.sleep(5)
            await send_screenshot(update, page, "📸 لقطة الشاشة بعد الفتح")

            # 1. التحقق من تسجيل الدخول
            if "Couldn't sign you in" in await page.content():
                await update.message.reply_text("❌ يرجى تسجيل الدخول. يرجى إرسال الكوكيز باستخدام /setcookies.")
                await browser.close()
                return

            # 2. محاولة الموافقة على الشروط
            steps = ["Get started", "Continue", "I understand", "Confirm", "Agree and continue"]
            for step in steps:
                try:
                    btn = page.get_by_text(step, exact=False)
                    if await btn.is_visible():
                        await btn.click()
                        await send_status(update, f"✅ تم الضغط على: {step}")
                        await asyncio.sleep(5)
                except:
                    continue

            # 3. الضغط على الموافقة (Agree and continue)
            await page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const agree = btns.find(b => b.textContent.toLowerCase().includes('agree and continue'));
                if (agree) agree.click();
            }''')

            # 4. الضغط على Deploy container
            await asyncio.sleep(5)
            try:
                await page.get_by_text("Deploy container", exact=False).click()
            except:
                pass

            # 5. إدخال بيانات الحاوية
            await send_status(update, "📦 جاري إدخال بيانات الحاوية...")
            await asyncio.sleep(15)
            try:
                input_field = page.locator('input[type="text"]').first
                await input_field.fill(container_image)
                await page.keyboard.press("Enter")
                await asyncio.sleep(5)

                # السماح بالوصول العام
                await page.click('label:has-text("Allow unauthenticated invocations")', timeout=5000)
            except:
                pass

            # 6. الضغط على Create
            await send_status(update, "🚀 جاري إنشاء الخدمة...")
            await page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const create = btns.find(b => b.textContent.trim() === 'Create');
                if (create) create.click();
            }''')

            # 7. انتظار الرابط
            await asyncio.sleep(60)
            await send_screenshot(update, page, "📸 المرحلة النهائية")

            try:
                link_el = await page.wait_for_selector('a[href*="run.app"]', timeout=30000)
                final_link = await link_el.get_attribute('href')
                await update.message.reply_text(f"🎉 تم النشر بنجاح! الرابط: {final_link}")
            except:
                await update.message.reply_text("⚠️ لم أتمكن من جلب الرابط. يرجى مراجعة الصورة.")

            await browser.close()

        except Exception as e:
            logger.error(f"Process Error: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")
            await browser.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ عذراً، هذا البوت مخصص للمالك فقط.")
        return
        
    await update.message.reply_text(
        "👋 أهلاً بك في بوت Google Cloud!\n\n"
        "1. أرسل الرابط وسأحاول النشر تلقائياً.\n"
        "2. إذا واجهت خطأ في تسجيل الدخول، يرجى إرسال الكوكيز (JSON) باستخدام الأمر /setcookies."
    )

async def set_cookies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id):
        await update.message.reply_text("⛔ عذراً، هذا البوت مخصص للمالك فقط.")
        return

    try:
        cookies_text = " ".join(context.args)
        cookies_json = json.loads(cookies_text)
        USER_COOKIES[user_id] = cookies_json
        await update.message.reply_text("✅ تم حفظ الكوكيز بنجاح! سأستخدمها في المرة القادمة.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في صيغة JSON: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    # التحقق من أن المستخدم هو المالك
    if not is_admin(user_id):
        await update.message.reply_text("⛔ عذراً، هذا البوت مخصص للمالك فقط.")
        return

    text = update.message.text
    if "http" not in text.lower():
        return

    await update.message.reply_text("🔍 بدأت العملية... سأقوم بإبلاغك بكل خطوة.")
    asyncio.create_task(deploy_on_gcp(update, text, CONTAINER_IMAGE, user_id))

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('setcookies', set_cookies))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    logger.info("Bot started...")
    app.run_polling()
