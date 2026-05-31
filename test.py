import serial
import time
import subprocess
import asyncio
import re
import random

from telegram import Update

from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes
)

# =====================================================
# SETTINGS
# =====================================================

BOT_TOKEN = "8732512915:AAGQWnqkvNBz3ua0ksmcF2G4Lu-GqUGmqyY"

CHAT_ID = 1890874299

PORT = "/dev/tty.usbmodem1101"

BAUD = 9600

# =====================================================
# SERIAL
# =====================================================

ser = serial.Serial(
    PORT,
    BAUD,
    timeout=1
)

time.sleep(2)

print("✅ Serial Connected")

# =====================================================
# STORAGE
# =====================================================

reminders = {}

# =====================================================
# BUTTON MESSAGES
# =====================================================

messages = {

    "WATER":
    "Patient needs water",

    "MEDICINE":
    "Patient needs medicine",

    "HELP":
    "Emergency help needed",

    "BATHROOM":
    "Patient needs bathroom"
}

# =====================================================
# SPEAK
# =====================================================

def speak(text):

    try:

        subprocess.run([
            "say",
            "-r",
            "155",
            text
        ])

    except:

        pass

# =====================================================
# TFT NORMAL MESSAGE
# =====================================================

def send_normal_message(text):

    try:

        ser.write(
            f"MSG:{text}\n".encode()
        )

    except Exception as e:

        print("Display Error:", e)

# =====================================================
# TFT REMINDER POPUP
# =====================================================

def send_reminder_popup(text):

    try:

        ser.write(
            f"REM:{text}\n".encode()
        )

    except Exception as e:

        print("Reminder Display Error:", e)

# =====================================================
# TELEGRAM SEND
# =====================================================

async def send_telegram(bot, text):

    try:

        await bot.send_message(
            chat_id=CHAT_ID,
            text=text
        )

        print("✅ Telegram Sent")

    except Exception as e:

        print("Telegram Error:", e)

# =====================================================
# GENERATE ID
# =====================================================

def generate_reminder_id():

    while True:

        rid = f"R{random.randint(10,99)}"

        if rid not in reminders:

            return rid

# =====================================================
# START
# =====================================================

async def start(update: Update,
                context: ContextTypes.DEFAULT_TYPE):

    txt = """
🏥 SMART PATIENT CARE SYSTEM

⏰ TIMER COMMANDS

/timer30sec Take medicine

/timer1min Drink water

/timer2mins BP tablet

📋 REMINDERS

/listreminders

/dropreminder R12

/dropreminders

⚡ OTHER

/status

/emergency

💬 Normal Text:
Speaks + TFT display
"""

    await update.message.reply_text(txt)

# =====================================================
# STATUS
# =====================================================

async def status(update: Update,
                 context: ContextTypes.DEFAULT_TYPE):

    txt = f"""
✅ SYSTEM STATUS

Serial Connected ✅

Port :
{PORT}

Baud :
{BAUD}

Active Reminders :
{len(reminders)}
"""

    await update.message.reply_text(txt)

# =====================================================
# REMINDER EXECUTION
# =====================================================

async def reminder_timer(bot,
                         rid,
                         seconds,
                         message):

    try:

        # WAIT UNTIL TIMER
        await asyncio.sleep(seconds)

        # =========================================
        # TRIGGER 3 TIMES
        # EVERY 5 SECONDS
        # =========================================

        for i in range(3):

            final_msg = f"""
⏰ REMINDER ALERT

🆔 {rid}

📝 {message}

🔔 Alert {i+1}/3
"""

            print(final_msg)

            # ================= VOICE =================

            speak(message)

            # ================= TFT =================

            send_reminder_popup(message)

            # ================= TELEGRAM =================

            await send_telegram(
                bot,
                final_msg
            )

            # ================= WAIT 5 SEC =================

            if i < 2:

                await asyncio.sleep(5)

        print(f"✅ Reminder Completed : {rid}")

        # REMOVE AFTER COMPLETE
        if rid in reminders:

            del reminders[rid]

    except asyncio.CancelledError:

        print(f"❌ Reminder Cancelled : {rid}")

# =====================================================
# TIMER COMMAND
# =====================================================

async def handle_timer(update: Update,
                       context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text.strip()

    # =================================================
    # SECONDS
    # =================================================

    match = re.match(
        r"/timer(\d+)sec\s+(.+)",
        text
    )

    if match:

        seconds = int(match.group(1))

        message = match.group(2)

    else:

        # =================================================
        # MINUTES
        # =================================================

        match = re.match(
            r"/timer(\d+)min[s]?\s+(.+)",
            text
        )

        if not match:

            await update.message.reply_text(
                """
❌ Examples

/timer30sec Take medicine

/timer1min Drink water

/timer2mins BP tablet
"""
            )

            return

        minutes = int(match.group(1))

        seconds = minutes * 60

        message = match.group(2)

    # =================================================
    # CREATE REMINDER
    # =================================================

    rid = generate_reminder_id()

    task = asyncio.create_task(

        reminder_timer(
            context.bot,
            rid,
            seconds,
            message
        )
    )

    reminders[rid] = {

        "task": task,

        "seconds": seconds,

        "message": message
    }

    await update.message.reply_text(
        f"""
✅ Reminder Created

🆔 ID :
{rid}

⏳ Time :
{seconds} sec

📝 Message :
{message}

🔔 Will repeat 3 times
⏱ Every 5 sec
"""
    )

# =====================================================
# LIST REMINDERS
# =====================================================

async def list_reminders(update: Update,
                         context: ContextTypes.DEFAULT_TYPE):

    if len(reminders) == 0:

        await update.message.reply_text(
            "📭 No active reminders."
        )

        return

    txt = "📋 ACTIVE REMINDERS\n\n"

    for rid, data in reminders.items():

        txt += (
            f"🆔 {rid}\n"
            f"⏳ {data['seconds']} sec\n"
            f"📝 {data['message']}\n\n"
        )

    await update.message.reply_text(txt)

# =====================================================
# DROP SINGLE
# =====================================================

async def drop_reminder(update: Update,
                        context: ContextTypes.DEFAULT_TYPE):

    if len(context.args) == 0:

        await update.message.reply_text(
            """
❌ Example

/dropreminder R12
"""
        )

        return

    rid = context.args[0].upper()

    if rid not in reminders:

        await update.message.reply_text(
            f"❌ {rid} not found."
        )

        return

    reminders[rid]["task"].cancel()

    del reminders[rid]

    await update.message.reply_text(
        f"🗑 Reminder {rid} deleted."
    )

# =====================================================
# DROP ALL
# =====================================================

async def drop_reminders(update: Update,
                         context: ContextTypes.DEFAULT_TYPE):

    for rid in list(reminders.keys()):

        reminders[rid]["task"].cancel()

        del reminders[rid]

    await update.message.reply_text(
        "🗑 All reminders deleted."
    )

# =====================================================
# EMERGENCY
# =====================================================

async def emergency(update: Update,
                    context: ContextTypes.DEFAULT_TYPE):

    ser.write(
        b"EMERGENCY\n"
    )

    await update.message.reply_text(
        "🚨 Emergency Triggered"
    )

# =====================================================
# NORMAL MESSAGE
# =====================================================

async def normal_message(update: Update,
                         context: ContextTypes.DEFAULT_TYPE):

    text = update.message.text

    print(f"Telegram → {text}")

    # ================= SPEAK =================

    speak(text)

    # ================= TFT =================

    send_normal_message(text)

    await update.message.reply_text(
        f"✅ Sent to Patient:\n{text}"
    )

# =====================================================
# SERIAL POLLING
# =====================================================

async def poll_serial(bot):

    buffer = ""

    while True:

        try:

            if ser.in_waiting > 0:

                char = ser.read().decode(
                    "utf-8",
                    errors="ignore"
                )

                if char == "\n":

                    line = buffer.strip().upper()

                    buffer = ""

                    if line != "":

                        print(f"[SERIAL] {line}")

                    # =====================================
                    # BUTTON PRESSED
                    # =====================================

                    if line in messages:

                        msg = messages[line]

                        print(f"Patient : {msg}")

                        # SPEAK
                        speak(msg)

                        # TELEGRAM
                        await send_telegram(
                            bot,
                            f"🔔 {msg}"
                        )

                    # =====================================
                    # SYSTEM START
                    # =====================================

                    elif line == "SYSTEM_STARTED":

                        print("✅ Arduino Started")

                        await send_telegram(
                            bot,
                            "✅ Patient Care System Started"
                        )

                else:

                    buffer += char

        except Exception as e:

            print("Serial Error:", e)

        await asyncio.sleep(0.05)

# =====================================================
# MAIN
# =====================================================

async def main():

    app = Application.builder().token(
        BOT_TOKEN
    ).build()

    # =================================================
    # COMMANDS
    # =================================================

    app.add_handler(
        CommandHandler(
            "start",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "help",
            start
        )
    )

    app.add_handler(
        CommandHandler(
            "status",
            status
        )
    )

    app.add_handler(
        CommandHandler(
            "listreminders",
            list_reminders
        )
    )

    app.add_handler(
        CommandHandler(
            "dropreminder",
            drop_reminder
        )
    )

    app.add_handler(
        CommandHandler(
            "dropreminders",
            drop_reminders
        )
    )

    app.add_handler(
        CommandHandler(
            "emergency",
            emergency
        )
    )

    # =================================================
    # TIMER
    # =================================================

    app.add_handler(
        MessageHandler(
            filters.Regex(r"^/timer"),
            handle_timer
        )
    )

    # =================================================
    # NORMAL TEXT
    # =================================================

    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND,
            normal_message
        )
    )

    bot = app.bot

    async with app:

        await app.start()

        await app.updater.start_polling()

        print("🤖 SMART SYSTEM RUNNING")

        print("📲 Listening Telegram + Touch")

        await poll_serial(bot)

        await app.updater.stop()

        await app.stop()

# =====================================================
# RUN
# =====================================================

if __name__ == "__main__":

    asyncio.run(main())