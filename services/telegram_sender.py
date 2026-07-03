from config import TELEGRAM_CHAT_ID


async def send_to_owner(app, message):
    if not TELEGRAM_CHAT_ID:
        print("TELEGRAM_CHAT_ID não configurado no .env")
        return

    await app.bot.send_message(
        chat_id=int(TELEGRAM_CHAT_ID),
        text=message
    )
