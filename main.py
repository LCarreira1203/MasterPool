import asyncio
import os
import threading
from datetime import datetime

from flask import Flask
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

from config import TELEGRAM_BOT_TOKEN
from services.market_prices import get_token_price
from services.pool_manager import add, delete, get_all, ensure_file, save_pools
from services.scheduler import start_background_tasks
from utils.messages import HELP_MESSAGE, WELCOME_MESSAGE


MASTERPOOL_MAIN_VERSION = "1.4-binance-only"

web_app = Flask(__name__)


@web_app.route("/")
def home():
    return "MasterPool online ✅"


@web_app.route("/health")
def health():
    return "OK ✅"


def money(value):
    try:
        return f"US$ {float(value):,.2f}"
    except Exception:
        return "Indisponível"


def money_brl(value):
    try:
        return f"R$ {float(value):,.2f}"
    except Exception:
        return "Indisponível"


def percent(value):
    try:
        return f"{float(value):.2f}%"
    except Exception:
        return "Indisponível"


def extract_symbol(text):
    symbol = (
        text.upper()
        .replace("/", "")
        .replace("-", "")
        .replace(" ", "")
        .replace("USDT", "")
        .replace("USDC", "")
        .replace("USD", "")
        .strip()
    )
    return symbol


def build_masterpool_report():
    ensure_file()
    pools = get_all()

    if not pools:
        return "Nenhuma pool cadastrada.\n\nUse:\n/addpool Orca SOL/USDC 1000 80 120"

    now = datetime.now().strftime("%d/%m/%Y %H:%M")
    msg = f"📊 RELATÓRIO MASTERPOOL\n🕒 {now}\n\n"

    for pool in pools:
        pool_id = pool.get("id", "?")
        dex = pool.get("dex", "-")
        pair = pool.get("pair", "-").upper()
        symbol = (pool.get("symbol") or pair.split("/")[0]).upper().strip()

        try:
            amount = float(pool.get("amount_invested", 0))
            range_min = float(pool.get("range_min", 0))
            range_max = float(pool.get("range_max", 0))
        except Exception:
            amount = 0.0
            range_min = 0.0
            range_max = 0.0

        price_data = get_token_price(symbol)
        price = price_data.get("price_usd")
        price_brl = price_data.get("price_brl")
        change_24h = price_data.get("change_24h", 0)
        source = price_data.get("source", "Binance")
        error = price_data.get("error")

        msg += (
            f"🏦 POOL #{pool_id}\n"
            f"DEX: {dex}\n"
            f"Par: {pair}\n"
            f"Token monitorado: {symbol}\n\n"
        )

        if price is None:
            msg += (
                "💰 Preço monitorado:\n"
                "Indisponível\n"
                f"📊 Fonte: {source}\n"
                f"⚠️ {error or 'Não consegui buscar o preço agora.'}\n\n"
                f"Valor aplicado: {money(amount)}\n\n"
                "📍 RANGE\n"
                f"Menor: {money(range_min)}\n"
                f"Maior: {money(range_max)}\n\n"
                "⚠️ Não consegui analisar o range agora.\n"
                "━━━━━━━━━━━━━━\n\n"
            )
            continue

        price = float(price)

        msg += (
            "💰 Preço monitorado:\n"
            f"{money(price)}\n"
        )

        if price_brl is not None:
            msg += f"{money_brl(price_brl)}\n"

        msg += (
            f"📈 Variação 24h: {change_24h}%\n"
            f"📊 Fonte: {source}\n\n"
            f"Valor aplicado: {money(amount)}\n\n"
            "📍 RANGE\n"
            f"Menor: {money(range_min)}\n"
            f"Maior: {money(range_max)}\n\n"
        )

        if range_min <= price <= range_max:
            dist_inf = ((price - range_min) / range_min) * 100 if range_min else 0
            dist_sup = ((range_max - price) / range_max) * 100 if range_max else 0

            if dist_inf <= 5:
                situacao = "🟡 Dentro do range, perto do limite inferior"
            elif dist_sup <= 5:
                situacao = "🟡 Dentro do range, perto do limite superior"
            else:
                situacao = "🟢 Dentro do range"

            msg += (
                f"📊 Situação: {situacao}\n"
                f"📉 Distância inferior: {percent(dist_inf)}\n"
                f"📈 Distância superior: {percent(dist_sup)}\n"
            )
        elif price < range_min:
            diff = ((range_min - price) / range_min) * 100 if range_min else 0
            msg += (
                "🚨 Situação: Fora do range abaixo do limite\n"
                f"📉 Abaixo do mínimo em: {percent(diff)}\n"
            )
        else:
            diff = ((price - range_max) / range_max) * 100 if range_max else 0
            msg += (
                "🚨 Situação: Fora do range acima do limite\n"
                f"📈 Acima do máximo em: {percent(diff)}\n"
            )

        msg += "━━━━━━━━━━━━━━\n\n"

    return msg.strip()


async def version(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(MASTERPOOL_MAIN_VERSION)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(WELCOME_MESSAGE)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(HELP_MESSAGE)


async def id_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"🆔 Seu CHAT_ID é:\n{update.effective_chat.id}")


async def bomdia(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_masterpool_report())


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(build_masterpool_report())


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
            "━━━━━━━━━━━━━━\n"
        )

    await update.message.reply_text(msg)


async def addpool(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

    symbol = pair.split("/")[0].strip().upper()

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


async def clearpools(update: Update, context: ContextTypes.DEFAULT_TYPE):
    save_pools({"pools": []})
    await update.message.reply_text("🧹 Todas as pools foram apagadas.")


async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query_text = " ".join(context.args).strip()

    if not query_text:
        await update.message.reply_text("Digite a cripto. Exemplo: /search sol")
        return

    symbol = extract_symbol(query_text)

    if not symbol:
        await update.message.reply_text("Digite uma cripto válida. Exemplo: /search sol")
        return

    price_data = get_token_price(symbol)

    if price_data["price_usd"] is None:
        await update.message.reply_text(
            f"⚠️ Não encontrei {symbol} na Binance.\n\n"
            "Confira o símbolo ou tente outro token."
        )
        return

    msg = (
        f"🪙 {symbol}\n\n"
        "💵 Preço agora:\n"
        f"US$ {price_data['price_usd']:,.2f}\n"
    )

    if price_data["price_brl"] is not None:
        msg += f"R$ {price_data['price_brl']:,.2f}\n"

    msg += (
        f"\n📈 24h: {price_data['change_24h']}%\n"
        f"📊 Fonte: {price_data['source']}\n\n"
        "Valor de referência para transação no momento."
    )

    await update.message.reply_text(msg)


async def post_init(app):
    await start_background_tasks(app)


def build_bot():
    if not TELEGRAM_BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN não encontrado. Configure no Render Environment.")

    ensure_file()

    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).post_init(post_init).build()

    app.add_handler(CommandHandler("version", version))
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("id", id_command))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("bomdia", bomdia))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("listpools", listpools))
    app.add_handler(CommandHandler("addpool", addpool))
    app.add_handler(CommandHandler("delpool", delpool))
    app.add_handler(CommandHandler("clearpools", clearpools))

    return app


def run_web():
    port = int(os.environ.get("PORT", 10000))
    print(f"Servidor web do MasterPool rodando na porta {port}...")
    web_app.run(host="0.0.0.0", port=port)


def main():
    print(f"MasterPool iniciando... versão {MASTERPOOL_MAIN_VERSION}")

    web_thread = threading.Thread(target=run_web, daemon=True)
    web_thread.start()

    bot = build_bot()

    print("MasterPool Telegram Bot rodando no processo principal...")
    bot.run_polling(
        allowed_updates=Update.ALL_TYPES,
        stop_signals=None,
    )


if __name__ == "__main__":
    main()
