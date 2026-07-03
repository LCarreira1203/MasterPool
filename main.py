import asyncio
import os
import threading

from flask import Flask
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

from config import TELEGRAM_BOT_TOKEN
from services.daily_report import build_daily_report
from services.market_prices import get_token_price
from services.pool_manager import add, delete, get_all, ensure_file
from services.scheduler import start_background_tasks
from utils.messages import WELCOME_MESSAGE, HELP_MESSAGE


web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "MasterPool online ✅"


@web_app.route("/health")
def health():
    return "OK ✅"


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_MESSAGE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_MESSAGE)


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Seu CHAT_ID é:\n{update.effective_chat.id}")


async def bomdia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_daily_report())


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_daily_report())


async def listpools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pools = get_all()

    if not pools:
        await update.message.reply_text("Nenhuma pool cadastrada.")
        return

    msg = "📋 POOLS CADASTRADAS\n\n"

    for pool in pools:
        msg += (
            f"ID: {pool['id']}\n"
            f"DEX: {pool['dex']}\n"
            f"Par: {pool['pair']}\n"
            f"Token monitorado: {pool.get('symbol', pool['pair'].split('/')[0])}\n"
            f"Valor aplicado: US$ {float(pool['amount_invested']):,.2f}\n"
            f"Range: US$ {float(pool['range_min']):,.2f} → US$ {float(pool['range_max']):,.2f}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(msg)


async def addpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Formato:
    # /addpool Orca SOL/USDC 1000 80 120
    args = context.args

    if len(args) != 5:
        await update.message.reply_text(
            "Use assim:\n\n"
            "/addpool Orca SOL/USDC 1000 80 120\n\n"
            "Formato:\n"
            "/addpool DEX PAR VALOR RANGE_MIN RANGE_MAX"
        )
        return

    dex = args[0].strip().capitalize()
    pair = args[1].upper().strip()

    if "/" not in pair:
        await update.message.reply_text("O par precisa estar nesse formato: SOL/USDC")
        return

    try:
        amount_invested = float(args[2].replace(",", "."))
        range_min = float(args[3].replace(",", "."))
        range_max = float(args[4].replace(",", "."))
    except ValueError:
        await update.message.reply_text(
            "Valor e ranges precisam ser números.\n\n"
            "Exemplo:\n/addpool Orca SOL/USDC 1000 80 120"
        )
        return

    if range_min >= range_max:
        await update.message.reply_text("O range mínimo precisa ser menor que o range máximo.")
        return

    symbol = pair.split("/")[0].strip()

    pool = {
        "dex": dex,
        "pair": pair,
        "symbol": symbol,
        "amount_invested": amount_invested,
        "range_min": range_min,
        "range_max": range_max,
        "active": True,
    }

    add(pool)

    await update.message.reply_text(
        "✅ Pool cadastrada!\n\n"
        f"DEX: {dex}\n"
        f"Par: {pair}\n"
        f"Token monitorado: {symbol}\n"
        f"Valor aplicado: US$ {amount_invested:,.2f}\n"
        f"Range: US$ {range_min:,.2f} → US$ {range_max:,.2f}"
    )


async def delpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Formato:
    # /delpool 1
    args = context.args

    if len(args) != 1:
        pools = get_all()

        if not pools:
            await update.message.reply_text("Nenhuma pool cadastrada para excluir.")
            return

        msg = "Para excluir, use:\n\n/delpool ID\n\nPools:\n"
        for pool in pools:
            msg += f"ID {pool['id']} - {pool['pair']} • {pool['dex']}\n"

        await update.message.reply_text(msg)
        return

    try:
        pool_id = int(args[0])
    except ValueError:
        await update.message.reply_text("O ID precisa ser um número. Exemplo: /delpool 1")
        return

    pools = get_all()
    pool = next((p for p in pools if int(p["id"]) == pool_id), None)

    if not pool:
        await update.message.reply_text("Pool não encontrada.")
        return

    delete(pool_id)

    await update.message.reply_text(f"✅ Pool excluída: {pool['pair']} • {pool['dex']}")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = " ".join(context.args).upper().strip()

    if not query_text:
        await update.message.reply_text("Digite a cripto. Exemplo: /search sol")
        return

    symbol = (
        query_text
        .replace("/", "")
        .replace("-", "")
        .replace(" ", "")
        .replace("USDT", "")
        .replace("USDC", "")
        .replace("USD", "")
        .strip()
    )

    if not symbol:
        await update.message.reply_text("Digite uma cripto válida. Exemplo: /search sol")
        return

    price_data = get_token_price(symbol)

    if price_data["price_usd"] is None:
        await update.message.reply_text(
            f"Não consegui buscar o preço real de {symbol} agora."
        )
        return

    msg = (
        f"🪙 {symbol}\n\n"
        f"💵 Preço agora:\n"
        f"US$ {price_data['price_usd']:,.2f}\n"
    )

    if price_data["price_brl"] is not None:
        msg += f"R$ {price_data['price_brl']:,.2f}\n"

    msg += (
        f"\n📈 24h: {price_data['change_24h']}%\n"
        f"📊 Fonte: {price_data['source']}\n\n"
        f"Valor de referência para transação no momento."
    )

    await update.message.reply_text(msg)


async def post_init(app):
    await start_background_tasks(app)


def build_bot():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN não encontrado. Configure no Render Environment.")

    ensure_file()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("bomdia", bomdia))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("listpools", listpools))
    app.add_handler(CommandHandler("addpool", addpool))
    app.add_handler(CommandHandler("delpool", delpool))

    return app


def run_bot():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    bot = build_bot()

    print("MasterPool Telegram Bot rodando...")
    bot.run_polling(
        allowed_updates=Update.ALL_TYPES,
        close_loop=False,
        stop_signals=None,
    )


def run_web():
    port = int(os.environ.get("PORT", 10000))
    print(f"Servidor web do MasterPool rodando na porta {port}...")
    web_app.run(host="0.0.0.0", port=port)


def main():
    print("MasterPool iniciando...")

    bot_thread = threading.Thread(target=run_bot, daemon=True)
    bot_thread.start()

    run_web()


if __name__ == "__main__":
    main()
