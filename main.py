import asyncio
import os

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
)

from config import TELEGRAM_BOT_TOKEN
from services.daily_report import build_daily_report
from services.market_prices import get_token_price
from services.pool_manager import add, delete, get_all, ensure_file
from services.scheduler import start_background_tasks
from utils.messages import WELCOME_MESSAGE, HELP_MESSAGE


DEX, PAIR, VALUE, RANGE_MIN, RANGE_MAX = range(5)


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

    msg = "🏦 POOLS CADASTRADAS\n\n"

    for pool in pools:
        msg += (
            f"ID: {pool['id']}\n"
            f"DEX: {pool['dex']}\n"
            f"Par: {pool['pair']}\n"
            f"Token monitorado: {pool.get('symbol', pool['pair'].split('/')[0])}\n"
            f"Valor aplicado: US$ {float(pool['amount_invested']):,.2f}\n"
            f"Range: US$ {pool['range_min']} → US$ {pool['range_max']}\n"
            f"━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(msg)


async def addpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("Orca", callback_data="dex_Orca")],
        [InlineKeyboardButton("Raydium", callback_data="dex_Raydium")],
        [InlineKeyboardButton("Meteora", callback_data="dex_Meteora")],
    ]

    await update.message.reply_text(
        "🏦 Vamos cadastrar uma nova pool.\n\nDex:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )

    return DEX


async def choose_dex(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    dex = query.data.replace("dex_", "")
    context.user_data["new_pool"] = {"dex": dex}

    await query.edit_message_text(
        f"Dex: {dex}\n\nAgora envie o par:\nExemplo: SOL/USDC"
    )

    return PAIR


async def receive_pair(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pair = update.message.text.upper().strip()

    if "/" not in pair:
        await update.message.reply_text("Digite o par nesse formato: SOL/USDC")
        return PAIR

    symbol = pair.split("/")[0].strip()

    context.user_data["new_pool"]["pair"] = pair
    context.user_data["new_pool"]["symbol"] = symbol

    await update.message.reply_text("Valor aplicado em dólar?\nExemplo: 1000")

    return VALUE


async def receive_value(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        value = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Digite apenas número. Exemplo: 1000")
        return VALUE

    context.user_data["new_pool"]["amount_invested"] = value

    await update.message.reply_text("Range menor em dólar?\nExemplo: 85")

    return RANGE_MIN


async def receive_range_min(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rmin = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Digite apenas número. Exemplo: 85")
        return RANGE_MIN

    context.user_data["new_pool"]["range_min"] = rmin

    await update.message.reply_text("Range maior em dólar?\nExemplo: 105")

    return RANGE_MAX


async def receive_range_max(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rmax = float(update.message.text.replace(",", "."))
    except ValueError:
        await update.message.reply_text("Digite apenas número. Exemplo: 105")
        return RANGE_MAX

    pool = context.user_data["new_pool"]
    pool["range_max"] = rmax
    pool["active"] = True

    add(pool)

    await update.message.reply_text(
        f"✅ Pool cadastrada!\n\n"
        f"DEX: {pool['dex']}\n"
        f"Par: {pool['pair']}\n"
        f"Token monitorado: {pool['symbol']}\n"
        f"Valor aplicado: US$ {float(pool['amount_invested']):,.2f}\n"
        f"Range: US$ {pool['range_min']} → US$ {pool['range_max']}"
    )

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Cadastro cancelado.")
    return ConversationHandler.END


async def delpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    pools = get_all()

    if not pools:
        await update.message.reply_text("Nenhuma pool cadastrada para excluir.")
        return

    keyboard = []

    for pool in pools:
        text = f"{pool['pair']} • {pool['dex']}"
        keyboard.append([InlineKeyboardButton(text, callback_data=f"del_{pool['id']}")])

    await update.message.reply_text(
        "Qual pool deseja excluir?",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def confirm_delpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    pool_id = int(query.data.replace("del_", ""))

    pools = get_all()
    pool = next((p for p in pools if int(p["id"]) == pool_id), None)

    if not pool:
        await query.edit_message_text("Pool não encontrada.")
        return

    keyboard = [
        [
            InlineKeyboardButton("✅ Sim, excluir", callback_data=f"confirmdel_{pool_id}"),
            InlineKeyboardButton("❌ Cancelar", callback_data="cancel_del"),
        ]
    ]

    await query.edit_message_text(
        f"⚠️ Excluir esta pool?\n\n{pool['pair']} • {pool['dex']}",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def execute_delpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "cancel_del":
        await query.edit_message_text("Exclusão cancelada.")
        return

    pool_id = int(query.data.replace("confirmdel_", ""))

    delete(pool_id)

    await query.edit_message_text("✅ Pool excluída com sucesso.")


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


def build_app():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN não encontrado. Configure no Render Environment.")

    ensure_file()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    addpool_handler = ConversationHandler(
        entry_points=[CommandHandler("addpool", addpool)],
        states={
            DEX: [CallbackQueryHandler(choose_dex, pattern="^dex_")],
            PAIR: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_pair)],
            VALUE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_value)],
            RANGE_MIN: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_range_min)],
            RANGE_MAX: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_range_max)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    app.add_handler(addpool_handler)
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("bomdia", bomdia))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("listpools", listpools))
    app.add_handler(CommandHandler("delpool", delpool))
    app.add_handler(CallbackQueryHandler(confirm_delpool, pattern="^del_"))
    app.add_handler(CallbackQueryHandler(execute_delpool, pattern="^(confirmdel_|cancel_del)"))

    return app


def main():
    print("MasterPool iniciando...")

    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    app = build_app()

    print("MasterPool rodando...")
    app.run_polling(
        allowed_updates=Update.ALL_TYPES,
        close_loop=False,
        stop_signals=None,
    )


if __name__ == "__main__":
    main()