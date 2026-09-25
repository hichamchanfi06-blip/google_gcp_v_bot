import asyncio
import logging
import os
import io
import json
import sys
from telegram import Update, Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler, MessageHandler, filters
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# ================== إعداداتك ==================
TELEGRAM_TOKEN = "8591926496:AAEjLJPFAz8L1IJn8Kj5187zitAZh2885nc"
ADMIN_ID = 8660614620
CHANNEL_LINK = "https://t.me/google_gcp_v"
CONTAINER_IMAGE = "dx02/aio_v2ray"
SERVICE_NAME = "vortex"
# ===============================================

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

bot = Bot(token=TELEGRAM_TOKEN)

async def send_to_channel(text):
    try:
        await bot.send_message(chat_id=CHANNEL_LINK, text=text)
    except Exception as e:
        logger.error(f"Failed to send to channel: {e}")

async def send_status(update, text):
    try:
        await update.message.reply_text(text)
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
            await send_status(update, "⏳ جاري فتح المتصفح وبدء عملية النشر...")
            
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage', '--disable-blink-features=AutomationControlled']
            )

            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
                viewport={'width': 1280, 'height': 800}
            )

            page = await context.new_page()
            stealth_applier = Stealth()
            await stealth_applier.apply_stealth_async(page)
            page.set_default_timeout(90000)

            await send_status(update, "🌐 جاري فتح رابط Google Skills...")
            await page.goto(url, wait_until='networkidle', timeout=90000)
            await asyncio.sleep(5)
            await send_screenshot(update, page, "📸 حالة الصفحة بعد الفتح")

            # التحقق من تسجيل الدخول
            if "Couldn't sign you in" in await page.content():
                await update.message.reply_text("❌ يرجى تسجيل الدخول أولاً. أرسل ملفات تعريف الارتباط /setcookies.")
                await browser.close()
                return

            # الضغط على الأزرار الأولية
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

            # الموافقة على شروط GCP
            await page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const agree = btns.find(b => b.textContent.toLowerCase().includes('agree and continue'));
                if (agree) agree.click();
            }''')
            await asyncio.sleep(5)

            # الضغط على Deploy container
            try:
                await page.get_by_text("Deploy container", exact=False).click()
            except:
                pass

            # إدخال بيانات الحاوية
            await send_status(update, "📦 جاري إدخال رابط الحاوية...")
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

            # ============ إعداد الخدمة (Service name) ============
            await send_status(update, "📝 جاري تعيين اسم الخدمة...")
            try:
                service_input = page.locator('input[aria-label="Service name"]')
                if await service_input.count() > 0:
                    await service_input.fill(SERVICE_NAME)
                else:
                    await page.locator('input[type="text"]').nth(1).fill(SERVICE_NAME)
                await asyncio.sleep(2)
            except Exception as e:
                logger.error(f"Service name error: {e}")

            # ============ إعدادات متقدمة ============
            await send_status(update, "⚙️ جاري ضبط الإعدادات المتقدمة...")
            
            # 1. ضبط الذاكرة إلى 2GiB
            try:
                mem_selector = 'div[role="combobox"][aria-label*="Memory"]'
                if await page.locator(mem_selector).count() > 0:
                    await page.locator(mem_selector).click()
                    await asyncio.sleep(1)
                    await page.get_by_text("2 GiB", exact=True).click()
                    await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Memory setting error: {e}")

            # 2. ضبط المهلة (Request timeout) إلى 3600
            try:
                timeout_input = page.locator('input[aria-label*="Request timeout"]')
                if await timeout_input.count() > 0:
                    await timeout_input.fill("3600")
                else:
                    await page.locator('input[type="number"]').first.fill("3600")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Timeout setting error: {e}")

            # 3. ضبط التزامن (Maximum concurrent requests) إلى 1000
            try:
                conc_input = page.locator('input[aria-label*="Maximum concurrent requests"]')
                if await conc_input.count() > 0:
                    await conc_input.fill("1000")
                else:
                    await page.locator('input[type="number"]').nth(1).fill("1000")
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Concurrency setting error: {e}")

            # الضغط على Create
            await send_status(update, "🚀 جاري الضغط على Create...")
            await page.evaluate('''() => {
                const btns = Array.from(document.querySelectorAll('button'));
                const create = btns.find(b => b.textContent.trim() === 'Create');
                if (create) create.click();
            }''')

            # انتظار الرابط
            await asyncio.sleep(60)
            await send_screenshot(update, page, "📸 المرحلة النهائية")

            try:
                link_el = await page.wait_for_selector('a[href*=".run.app"]', timeout=30000)
                final_link = await link_el.get_attribute('href')
                msg = f"✅ تم النشر بنجاح! اسم الخدمة: {SERVICE_NAME}\nالرابط: {final_link}"
                await update.message.reply_text(msg)
                await send_to_channel(f"🚀 تم نشر خدمة جديدة!\n{msg}")
            except:
                await update.message.reply_text("⚠️ لم أتمكن من جلب الرابط. يرجى مراجعة الصورة.")
                await send_to_channel("⚠️ فشل في جلب الرابط بعد النشر.")

            await browser.close()

        except Exception as e:
            logger.error(f"Process Error: {e}")
            await update.message.reply_text(f"❌ خطأ: {str(e)}")
            await send_to_channel(f"❌ فشل النشر: {str(e)}")
            await browser.close()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت Google Cloud!\n\n"
        "1. أرسل الرابط وسأحاول النشر تلقائياً.\n"
        "2. إذا واجهت خطأ في تسجيل الدخول، استخدم /setcookies."
    )

async def set_cookies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    try:
        cookies_text = " ".join(context.args)
        cookies_json = json.loads(cookies_text)
        await update.message.reply_text("✅ تم حفظ الكوكيز بنجاح! سأستخدمها في المرة القادمة.")
    except Exception as e:
        await update.message.reply_text(f"❌ خطأ في تنسيق JSON: {str(e)}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "http" not in text.lower():
        return

    user_id = update.effective_user.id
    await update.message.reply_text("⏳ بدأ العمل... سيتم إشعارك عند الانتهاء.")
    asyncio.create_task(deploy_on_gcp(update, text, CONTAINER_IMAGE, user_id))

if __name__ == '__main__':
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler('start', start))
    app.add_handler(CommandHandler('setcookies', set_cookies))
    app.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    logger.info("Bot started...")
    app.run_polling()
