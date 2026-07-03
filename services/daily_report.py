from datetime import datetime
from zoneinfo import ZoneInfo

from services.market_prices import get_token_price, get_unique_symbols_from_pools
from services.pool_manager import get_all
from services.price_monitor import analyze_pool


TZ = ZoneInfo("America/Sao_Paulo")


def money_usd(value):
    if value is None:
        return "Indisponível"
    return f"US$ {float(value):,.2f}"


def money_brl(value):
    if value is None:
        return "Indisponível"
    return f"R$ {float(value):,.2f}"


def build_token_prices_section(pools):
    symbols = get_unique_symbols_from_pools(pools)

    if not symbols:
        return ""

    msg = "💲 COTAÇÕES DAS MOEDAS DAS POOLS\n\n"

    for symbol in symbols:
        price_data = get_token_price(symbol)

        msg += (
            f"🪙 {symbol}\n"
            f"US$: {money_usd(price_data['price_usd'])}\n"
            f"R$: {money_brl(price_data['price_brl'])}\n"
        )

        if price_data["change_24h"] is not None:
            msg += f"24h: {price_data['change_24h']}%\n"

        if price_data["source"]:
            msg += f"Fonte: {price_data['source']}\n"

        msg += "\n"

    msg += "━━━━━━━━━━━━━━\n\n"
    return msg


def build_daily_report():
    pools = get_all()
    now = datetime.now(TZ)

    if not pools:
        return "☀️ BOM DIA, LUIZ!\n\nNenhuma pool cadastrada."

    msg = (
        "☀️ BOM DIA, LUIZ!\n\n"
        f"📅 {now.strftime('%d/%m/%Y')}\n"
        f"⏰ {now.strftime('%H:%M')}\n\n"
    )

    msg += build_token_prices_section(pools)
    msg += "📊 RELATÓRIO MASTERPOOL\n\n"

    for pool in pools:
        pool, analysis = analyze_pool(pool)

        if analysis is None:
            msg += (
                f"🏦 {pool['pair']} • {pool['dex']}\n"
                "Não consegui buscar o preço agora.\n\n"
                "━━━━━━━━━━━━━━\n\n"
            )
            continue

        price = analysis["price"]
        price_brl = analysis["price_brl"]
        change = analysis["change_24h"]
        dist_lower = analysis["dist_lower"]
        dist_upper = analysis["dist_upper"]

        if analysis["below_range"]:
            status = "🔴 Fora do range inferior"
        elif analysis["above_range"]:
            status = "🔴 Fora do range superior"
        elif 0 <= dist_lower <= 5:
            status = "🟡 Próximo do range inferior"
        elif 0 <= dist_upper <= 5:
            status = "🟡 Próximo do range superior"
        else:
            status = "🟢 Dentro do range"

        msg += (
            f"🏦 POOL #{pool['id']}\n"
            f"DEX: {pool['dex']}\n"
            f"Par: {pool['pair']}\n"
            f"Token monitorado: {analysis['symbol']}\n\n"
            f"💰 Preço monitorado:\n"
            f"{money_usd(price)}\n"
            f"{money_brl(price_brl)}\n"
            f"📈 Variação 24h: {change}%\n"
            f"Fonte: {analysis['source']}\n\n"
            f"Valor aplicado: US$ {float(pool['amount_invested']):,.2f}\n\n"
            f"📍 RANGE\n"
            f"Menor: US$ {float(pool['range_min']):,.2f}\n"
            f"Maior: US$ {float(pool['range_max']):,.2f}\n\n"
            f"📊 Situação: {status}\n"
            f"📏 Distância inferior: {dist_lower:.2f}%\n"
            f"📏 Distância superior: {dist_upper:.2f}%\n\n"
            "━━━━━━━━━━━━━━\n\n"
        )

    return msg
