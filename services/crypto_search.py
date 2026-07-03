import requests
from config import DEXSCREENER_SEARCH_URL


def search_crypto(query: str):
    """Busca tokens/pools na API da Dexscreener."""
    if not query or not query.strip():
        return None, "Digite o nome, símbolo ou contrato da cripto. Exemplo: /search sol"

    try:
        response = requests.get(
            DEXSCREENER_SEARCH_URL,
            params={"q": query.strip()},
            timeout=15,
        )
        response.raise_for_status()
        data = response.json()
    except requests.RequestException as error:
        return None, f"Erro ao buscar na Dexscreener: {error}"

    pairs = data.get("pairs", []) or []
    if not pairs:
        return None, "Nenhum resultado encontrado. Tente outro nome, símbolo ou contrato."

    pairs = sorted(
        pairs,
        key=lambda p: float((p.get("liquidity") or {}).get("usd") or 0),
        reverse=True,
    )

    return pairs[:5], None
