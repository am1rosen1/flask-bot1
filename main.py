import asyncio
import os
import time
from telethon import TelegramClient, errors
from telethon.sessions import StringSession
from telethon.errors import FloodWaitError
from telethon.tl.functions.channels import JoinChannelRequest
from telethon.tl.functions.messages import ImportChatInviteRequest
from telethon.errors import MessageIdInvalidError
from telethon.tl.types import Updates, UpdateNewMessage, UpdateNewChannelMessage
from flask import Flask
from threading import Thread

# بقیه ایمپورت‌های خودت مثل telethon و asyncio و ...

app = Flask('')

@app.route('/')
def home():
    return "✅ Bot is running."

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# 🧠 اینو قبل از اجرای اصلی برنامه صدا بزن:
keep_alive()

# تنظیمات اصلی
api_id = 29014935  # API ID شما
api_hash = '4fd0256687178b8988295a00aec42f5d'  # API Hash شما
phone_number = '+989023996712'
SESSION_FILE = 'session.txt'
LINKS_FILE = 'links.txt'
UNABLE_FILE = 'unable.txt'
MAX_TRIES = 3  # تعداد تلاش‌های مجاز
WAIT_TIME = 5  # مدت زمان انتظار بین هر تلاش (به ثانیه)


async def init_client():
    if os.path.exists(SESSION_FILE):
        try:
            with open(SESSION_FILE, 'r') as f:
                session_str = f.read().strip()
            client = TelegramClient(StringSession(session_str), api_id,
                                    api_hash)
            await client.connect()
            print("✅ اتصال با استفاده از session موجود برقرار شد.")
        except Exception as e:
            print(
                f"⚠️ خطا در بارگذاری session: {e} | تلاش برای ایجاد session جدید..."
            )
            client = TelegramClient(StringSession(), api_id, api_hash)
            await client.start(phone_number)
            session_str = client.session.save()
            with open(SESSION_FILE, 'w') as f:
                f.write(session_str)
    else:
        print("📦 فایل session پیدا نشد. در حال ساخت session جدید...")
        client = TelegramClient(StringSession(), api_id, api_hash)
        await client.start(phone_number)
        session_str = client.session.save()
        with open(SESSION_FILE, 'w') as f:
            f.write(session_str)

    if not await client.is_user_authorized():
        await client.send_code_request(phone_number)
        code = input("📩 لطفاً کد تأیید را وارد کنید: ")
        await client.sign_in(phone_number, code)

    return client


async def join_and_test(client, link):
    attempt = 0  # شمارش تعداد تلاش‌ها

    while attempt < MAX_TRIES:
        attempt += 1
        try:
            print(f"🚪 در حال تلاش برای پیوستن به: {link}")
            if '/+' in link or 'joinchat' in link:
                invite_hash = link.split('/')[-1].replace('+', '')
                try:
                    entity = await client(ImportChatInviteRequest(invite_hash))
                    print("✅ با موفقیت به گروه/کانال با لینک دعوت پیوستیم.")
                except Exception as e:
                    print(f"❌ خطا در جوین شدن با لینک دعوت: {e}")
                    with open("unable_to_join.txt", 'a') as f:
                        f.write(link + '\n')
                    break
            else:
                username = link.split('/')[-1]
                entity = await client.get_entity(username)
                await client(JoinChannelRequest(entity))
                print("✅ با موفقیت به گروه/کانال عمومی پیوستیم.")

            await asyncio.sleep(2)

            # تلاش برای ارسال پیام تست
            try:
                result = await client.send_message(link, "سلام♥")
                real_msg = None
                if isinstance(result, Updates):
                    for update in result.updates:
                        if isinstance(
                                update,
                            (UpdateNewMessage, UpdateNewChannelMessage)):
                            real_msg = update.message
                            break
                else:
                    real_msg = result

                await asyncio.sleep(10)

                # بررسی وجود پیام
                if real_msg:
                    msg = await client.get_messages(link, ids=real_msg.id)
                    if msg:
                        print("🔍 پیام با موفقیت از سرور بازیابی شد.")
                    else:
                        print("پیام توسط ربات ها پاک شده است")
                        with open("unable_to_join.txt", 'a') as f:
                            f.write(link + '\n')
                else:
                    print("⚠️ پیامی برای بررسی نداشتیم.")
            except Exception as e:
                print(f"❌ خطا: {e}")
                with open("unable_to_join.txt", 'a') as f:
                    f.write(link + '\n')
            break
        except FloodWaitError as e:
            # اگر با ارور FloodWaitError مواجه شدیم، منتظر می‌مانیم و دوباره تلاش می‌کنیم
            print(f"❌ نیاز به صبر {e.seconds} ثانیه است. منتظر می‌مانیم.")
            await asyncio.sleep(e.seconds)

        except Exception as e:
            msg = str(e)
            if "already a participant" in msg:
                print("ℹ️ کاربر قبلاً عضو این گروه بوده.")
                break  # نیازی به تلاش مجدد نیست
            elif "A wait of" in msg and "is required" in msg:
                seconds = int(''.join([c for c in msg if c.isdigit()]))
                print(f"⏳ نیاز به صبر {seconds} ثانیه. صبر می‌کنیم...")
                await asyncio.sleep(seconds)
                continue
            else:
                print(f"❌ خطا در جوین شدن به {link}: {e}")
                with open("unable_to_join.txt", 'a') as f:
                    f.write(link + '\n')

        # اگر تعداد تلاش‌ها کمتر از MAX_TRIES باشد، کمی صبر می‌کنیم
        if attempt < MAX_TRIES - 1:
            print(f"🔄 تلاش مجدد در {WAIT_TIME} ثانیه دیگر...")
            await asyncio.sleep(WAIT_TIME)

async def get_total_dialogs_count(client):
    dialogs = await client.get_dialogs()
    count = sum(1 for dialog in dialogs if getattr(dialog.entity, 'megagroup', False) or getattr(dialog.entity, 'broadcast', False))
    return count

async def main():
    client = await init_client()

    with open('links.txt', 'r') as f:
        links = [line.strip() for line in f if line.strip()]

    index = 0
    while index < len(links):
        total = await get_total_dialogs_count(client)
        if total >= 475:
            print(f"🚫 به حداکثر تعداد عضویت (475) رسیدیم. در حالت انتظار قرار می‌گیریم...")
            while total >= 475:
                print("⏳ در حال بررسی هر ۳ دقیقه برای ادامه...")
                await asyncio.sleep(180)  # 3 دقیقه صبر
                total = await get_total_dialogs_count(client)
            print("✅ ظرفیت آزاد شد، ادامه می‌دهیم...")
        success = False
        for attempt in range(3):
            if index >= len(links):
                break
            link = links[index]
            try:
                await join_and_test(client, link)
                success = True
                index += 1  # برو به لینک بعدی و تلاش کن
                await asyncio.sleep(1200)
                break  # از حلقه بیرون برو چون موفق شدیم
            except:
                break
        if not success:
            print(
                "⏳ سه تلاش انجام شد ولی هیچ‌کدام موفق نبود. ۲ دقیقه صبر می‌کنیم..."
            )
            await asyncio.sleep(120)

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())