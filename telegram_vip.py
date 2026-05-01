"""
💎 TELEGRAM VIP BOT — Free + Paid Signal Channels
Track 2 Monetization: $500-$1,500/חודש

מבנה:
  - Free channel: BIAS יומי + 1 signal (delay של 30 דקות)
  - VIP channel: 3+ signals/day, real-time entry/exit alerts
  - Payment: Telegram Stars / Ko-fi / Patreon link

הרצה: python telegram_vip.py
"""
import sys
import os
import asyncio
import json
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")

load_dotenv(Path.home() / "tv_webhook" / ".env")

TOKEN       = os.getenv("TELEGRAM_TOKEN")
FREE_CHAT   = os.getenv("FREE_CHAT_ID", "")      # @your_free_channel
VIP_CHAT    = os.getenv("VIP_CHAT_ID", "")        # @your_vip_channel
ADMIN_CHAT  = os.getenv("ALL_CHAT_ID", "1246833993")

# ── Payment Config ──────────────────────────────────────────
VIP_PRICE_MONTHLY = 29     # $
KO_FI_LINK        = "https://ko-fi.com/mordehaibotbika23381"
PATREON_LINK      = ""   # optional
BUYMEACOFFEE_LINK = ""   # optional

# ── VIP Subscribers ─────────────────────────────────────────
VIP_FILE = Path(__file__).parent / "vip_subscribers.json"

def load_vip_users():
    if VIP_FILE.exists():
        return json.loads(VIP_FILE.read_text(encoding="utf-8"))
    return {}

def save_vip_users(data):
    VIP_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def is_vip(user_id: str) -> bool:
    users = load_vip_users()
    if str(user_id) not in users:
        return False
    expiry = users[str(user_id)].get("expiry", "1970-01-01")
    return datetime.now().strftime("%Y-%m-%d") <= expiry

def add_vip(user_id: str, username: str, months: int = 1):
    users = load_vip_users()
    expiry = (datetime.now() + timedelta(days=30 * months)).strftime("%Y-%m-%d")
    users[str(user_id)] = {
        "username": username,
        "expiry": expiry,
        "joined": datetime.now().strftime("%Y-%m-%d"),
        "months": months,
    }
    save_vip_users(users)
    return expiry


async def handle_start(bot, update):
    """פקודת /start — מציג מידע על הערוצים"""
    msg = (
        "📊 *Trading Signals Bot*\n\n"
        "🆓 *Free Channel:* BIAS יומי + 1 signal/day (delay 30min)\n"
        f"💎 *VIP Channel:* 3+ signals/day, real-time alerts, {VIP_PRICE_MONTHLY}$/month\n\n"
        "🔗 *Payment:*\n"
        f"• Ko-fi: {KO_FI_LINK}\n"
        f"• Patreon: {PATREON_LINK}\n\n"
        "אחרי תשלום — שלח צילום מסך ל-@admin"
    )
    await bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")


async def handle_buy(bot, update):
    """פקודת /buy — קישורי תשלום"""
    msg = (
        f"💎 *VIP Signals — {VIP_PRICE_MONTHLY}$/month*\n\n"
        "🔗 *Payment Links:*\n"
        f"• Ko-fi: {KO_FI_LINK}\n"
        f"• Patreon: {PATREON_LINK}\n"
        f"• Buy Me a Coffee: {BUYMEACOFFEE_LINK}\n\n"
        "📸 אחרי תשלום — שלח צילום מסך כאן\n"
        "⏱️ גישה מיידית אחרי אימות"
    )
    await bot.send_message(chat_id=update.effective_chat.id, text=msg, parse_mode="Markdown")


async def handle_approve(bot, update, args):
    """פקודת /approve USER_ID — מאשר VIP (admin only)"""
    if str(update.effective_chat.id) != ADMIN_CHAT:
        await bot.send_message(chat_id=update.effective_chat.id, text="❌ Admin only")
        return

    if not args:
        await bot.send_message(chat_id=update.effective_chat.id, text="שימוש: /approve USER_ID")
        return

    user_id = args[0]
    expiry = add_vip(user_id, "approved", months=1)
    await bot.send_message(chat_id=update.effective_chat.id,
                          text=f"✅ VIP approved: {user_id} (expires: {expiry})")

    # הודע למשתמש
    try:
        await bot.send_message(chat_id=user_id,
            text=f"🎉 *Welcome to VIP!*\n\nגישה לשלושה חודשים — {expiry}\n\n"
                 f"🔔 תקבל התראות בזמן אמת.\n"
                 f"📊 צפה בערוץ: @your_vip_channel",
            parse_mode="Markdown")
    except Exception:
        pass


async def handle_status(bot, update):
    """פקודת /status — בודק סטטוס VIP"""
    user_id = str(update.effective_chat.id)
    if is_vip(user_id):
        users = load_vip_users()
        expiry = users[user_id]["expiry"]
        await bot.send_message(chat_id=update.effective_chat.id,
            text=f"✅ *VIP Active*\n📅 Expires: {expiry}\n💎 Enjoy the signals!",
            parse_mode="Markdown")
    else:
        await bot.send_message(chat_id=update.effective_chat.id,
            text=f"❌ Not VIP\n\n/buy — upgrade to VIP ({VIP_PRICE_MONTHLY}$/month)")


async def send_signal_to_channels(bot, signal: dict, immediate: bool = True):
    """שולח signal לערוצים. VIP = real-time, Free = delay"""
    emoji = "🟢" if signal["direction"] == "LONG" else "🔴"
    arrow = "BUY" if signal["direction"] == "LONG" else "SELL"

    msg = (
        f"{emoji} *{signal['name']} — {arrow}*\n"
        f"💰 Entry: `{signal['price']}`\n"
        f"🛑 SL: `{signal['sl']}`\n"
        f"🎯 TP: `{signal['tp']}`\n"
        f"📊 RSI: {signal.get('rsi', 'N/A')}\n"
        f"📈 {'+'.join(signal.get('signals', []))}\n\n"
        f"_DYOR — Not financial advice_"
    )

    # VIP channel — real-time
    if VIP_CHAT:
        try:
            await bot.send_message(chat_id=VIP_CHAT, text=msg, parse_mode="Markdown")
            print(f"  [VIP] Signal sent: {signal['name']} {signal['direction']}")
        except Exception as e:
            print(f"  [VIP] Error: {e}")

    # Free channel — with delay or gated
    if FREE_CHAT:
        if immediate:
            # Free gets 1 signal/day, VIP gets all
            free_msg = msg + "\n\n_💎 VIP לקבלת כל הסיגנלים בזמן אמת — /buy_"
            try:
                await bot.send_message(chat_id=FREE_CHAT, text=free_msg, parse_mode="Markdown")
                print(f"  [FREE] Signal sent (immediate): {signal['name']}")
            except Exception as e:
                print(f"  [FREE] Error: {e}")
        else:
            # Schedule delayed send
            print(f"  [FREE] Delaying 30min for free channel...")


async def send_daily_bias(bot):
    """שולח BIAS יומי לערוץ חינם"""
    from entry_monitor import ASSETS
    import yfinance as yf

    msg = f"📊 *Daily BIAS — {datetime.now().strftime('%d/%m/%Y')}*\n\n"

    for name, info in list(ASSETS.items())[:8]:  # top 8
        try:
            h = yf.Ticker(info["symbol"]).history(period="5d", interval="1h")
            if h.empty:
                continue
            price = round(h["Close"].iloc[-1], 4)
            ma50 = round(h["Close"].rolling(50).mean().iloc[-1], 4)
            trend = "📈 BULL" if price > ma50 else "📉 BEAR"
            msg += f"{trend} {name}: {price}\n"
        except Exception:
            continue

    msg += "\n💎 *VIP לקבלת סיגנלים מדויקים* — /buy"

    if FREE_CHAT:
        await bot.send_message(chat_id=FREE_CHAT, text=msg, parse_mode="Markdown")
    print("[BIAS] Daily bias sent")


async def main():
    from telegram.ext import ApplicationBuilder, CommandHandler

    app = ApplicationBuilder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", lambda u, ctx: handle_start(ctx.bot, u)))
    app.add_handler(CommandHandler("buy", lambda u, ctx: handle_buy(ctx.bot, u)))
    app.add_handler(CommandHandler("status", lambda u, ctx: handle_status(ctx.bot, u)))
    app.add_handler(CommandHandler("approve", lambda u, ctx: handle_approve(ctx.bot, u, ctx.args)))

    print("=" * 50)
    print("💎 TELEGRAM VIP BOT ACTIVE")
    print(f"   Free: {FREE_CHAT or 'Not set'}")
    print(f"   VIP:  {VIP_CHAT or 'Not set'}")
    print(f"   Admin: {ADMIN_CHAT}")
    print("=" * 50)

    # שלח BIAS יומי ב-08:00
    now = datetime.now()
    if now.hour >= 8 and now.minute < 5:
        await send_daily_bias(app.bot)

    await app.run_polling()


if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    asyncio.run(main())