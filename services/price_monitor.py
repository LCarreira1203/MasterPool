from services.market_prices import get_token_price


def get_price(symbol):
    data = get_token_price(symbol)

    if data["price_usd"] is None:
        return None, None

    return data["price_usd"], data["change_24h"]


def distance_to_ranges(price, range_min, range_max):
    dist_lower = ((price - range_min) / range_min) * 100
    dist_upper = ((range_max - price) / range_max) * 100
    return dist_lower, dist_upper


def analyze_pool(pool):
    symbol = pool.get("symbol")

    if not symbol:
        symbol = pool["pair"].split("/")[0].upper().strip()
        pool["symbol"] = symbol

    price_data = get_token_price(symbol)
    price = price_data["price_usd"]

    if price is None:
        return pool, None

    range_min = float(pool["range_min"])
    range_max = float(pool["range_max"])

    dist_lower, dist_upper = distance_to_ranges(price, range_min, range_max)

    analysis = {
        "symbol": symbol,
        "price": price,
        "price_brl": price_data["price_brl"],
        "change_24h": price_data["change_24h"],
        "source": price_data["source"],
        "dist_lower": dist_lower,
        "dist_upper": dist_upper,
        "in_range": range_min <= price <= range_max,
        "below_range": price < range_min,
        "above_range": price > range_max,
    }

    return pool, analysis


def check_alerts(pool, analysis):
    alerts = []

    if analysis is None:
        return alerts, pool

    price = analysis["price"]
    symbol = analysis["symbol"]
    dist_lower = analysis["dist_lower"]
    dist_upper = analysis["dist_upper"]

    range_min = float(pool["range_min"])
    range_max = float(pool["range_max"])

    pool.setdefault("alert_lower_sent", False)
    pool.setdefault("alert_upper_sent", False)
    pool.setdefault("out_of_range_sent", False)

    if price < range_min or price > range_max:
        if not pool["out_of_range_sent"]:
            if price < range_min:
                side = "inferior"
                limit = range_min
            else:
                side = "superior"
                limit = range_max

            alerts.append(
                (
                    f"🚨 MASTERPOOL\n\n"
                    f"Sua pool saiu do range.\n\n"
                    f"Pool: {pool['pair']} • {pool['dex']}\n"
                    f"Cripto: {symbol}\n\n"
                    f"Preço atual: US$ {price:,.2f}\n"
                    f"Limite {side}: US$ {limit:,.2f}\n"
                    f"Range: US$ {range_min:,.2f} → US$ {range_max:,.2f}\n\n"
                    f"A posição pode ter deixado de gerar taxas."
                )
            )

            pool["out_of_range_sent"] = True

        return alerts, pool

    pool["out_of_range_sent"] = False

    if 0 <= dist_lower <= 5:
        if not pool["alert_lower_sent"]:
            alerts.append(
                (
                    f"⚠️ ALERTA MASTERPOOL\n\n"
                    f"A {symbol} está a 5% ou menos do range inferior.\n\n"
                    f"Pool: {pool['pair']} • {pool['dex']}\n"
                    f"Preço atual: US$ {price:,.2f}\n"
                    f"Limite inferior: US$ {range_min:,.2f}\n"
                    f"Distância: {dist_lower:.2f}%"
                )
            )
            pool["alert_lower_sent"] = True
    elif dist_lower > 5:
        pool["alert_lower_sent"] = False

    if 0 <= dist_upper <= 5:
        if not pool["alert_upper_sent"]:
            alerts.append(
                (
                    f"⚠️ ALERTA MASTERPOOL\n\n"
                    f"A {symbol} está a 5% ou menos do range superior.\n\n"
                    f"Pool: {pool['pair']} • {pool['dex']}\n"
                    f"Preço atual: US$ {price:,.2f}\n"
                    f"Limite superior: US$ {range_max:,.2f}\n"
                    f"Distância: {dist_upper:.2f}%"
                )
            )
            pool["alert_upper_sent"] = True
    elif dist_upper > 5:
        pool["alert_upper_sent"] = False

    return alerts, pool
