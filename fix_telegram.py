"""
מוצא ומגדיר את ה-chat_id הנכון לטלגרם
הרץ את זה אחרי ששלחת /start לבוט
"""
import asyncio, os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path.home() / "tv_webhook" / ".env")

TOKEN = os.getenv("TELEGRAM_TOKEN")
ENV_PATH = Path.home() / "tv_webhook" / ".env"


async def main():
    import telegram
    if not TOKEN:
        print("[ERROR] אין TELEGRAM_TOKEN ב-.env")
        return

    bot = telegram.Bot(token=TOKEN)
    me = await bot.get_me()
    print(f"\nבוט: @{me.username} (ID: {me.id})")
    print("=" * 40)

    # מחפש updates
    updates = await bot.get_updates(limit=20)
    if not updates:
        print(f"\n❌ אין הודעות!")
        print(f"   1. פתח טלגרם")
        print(f"   2. חפש @{me.username}")
        print(f"   3. שלח /start")
        print(f"   4. הרץ שוב את הסקריפט")
        return

    print("\nצ'אטים שנמצאו:")
    seen = set()
    for u in updates:
        msg = u.message or u.channel_post
        if not msg:
            continue
        cid  = msg.chat.id
        name = msg.chat.first_name or msg.chat.title or str(cid)
        ctype = msg.chat.type
        if cid in seen:
            continue
        seen.add(cid)
        print(f"  chat_id: {cid} | שם: {name} | סוג: {ctype}")

        # שליחת הודעת אישור
        try:
            await bot.send_message(chat_id=cid,
                text=f"✅ Diamond Scanner מחובר!\nID: {cid}")
            print(f"  -> הודעת אישור נשלחה!")
        except Exception as e:
            print(f"  -> שגיאה: {e}")

    # עדכון .env
    if seen:
        best_id = list(seen)[0]
        content = ENV_PATH.read_text(encoding="utf-8")

        if "ALL_CHAT_ID=" in content:
            lines = []
            for line in content.splitlines():
                if line.startswith("ALL_CHAT_ID="):
                    lines.append(f"ALL_CHAT_ID={best_id}")
                else:
                    lines.append(line)
            content = "\n".join(lines)
        else:
            content += f"\nALL_CHAT_ID={best_id}"

        ENV_PATH.write_text(content, encoding="utf-8")
        print(f"\n✅ .env עודכן: ALL_CHAT_ID={best_id}")
        print("   הרץ עכשיו: python diamond_scanner.py")


asyncio.run(main())
