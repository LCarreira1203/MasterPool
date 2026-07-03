import json
import os

POOLS_FILE = "data/pools.json"


def ensure_file():
    os.makedirs("data", exist_ok=True)

    if not os.path.exists(POOLS_FILE):
        with open(POOLS_FILE, "w", encoding="utf-8") as f:
            json.dump({"pools": []}, f, indent=4)


def load_pools():
    ensure_file()

    try:
        with open(POOLS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        data = {"pools": []}
        save_pools(data)

    if "pools" not in data or not isinstance(data["pools"], list):
        data = {"pools": []}
        save_pools(data)

    return data


def save_pools(data):
    with open(POOLS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)


def get_all():
    return load_pools()["pools"]


def add(pool):
    data = load_pools()
    pools = data["pools"]

    pool["id"] = 1 if not pools else max(int(p.get("id", 0)) for p in pools) + 1
    pool["alert_lower_sent"] = False
    pool["alert_upper_sent"] = False
    pool["out_of_range_sent"] = False

    pools.append(pool)
    save_pools(data)


def delete(pool_id):
    data = load_pools()
    data["pools"] = [p for p in data["pools"] if int(p["id"]) != int(pool_id)]
    save_pools(data)


def update(pool):
    data = load_pools()

    for i, p in enumerate(data["pools"]):
        if int(p["id"]) == int(pool["id"]):
            data["pools"][i] = pool
            break

    save_pools(data)
