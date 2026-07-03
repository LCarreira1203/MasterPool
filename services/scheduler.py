import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo

from services.daily_report import build_daily_report
from services.pool_manager import get_all, update
from services.price_monitor import analyze_pool, check_alerts
from services.telegram_sender import send_to_owner


TZ = ZoneInfo("America/Sao_Paulo")


async def daily_report_loop(app):
    sent_today = None

    while True:
        now = datetime.now(TZ)

        if now.hour == 9 and now.minute == 0:
            today = now.date().isoformat()

            if sent_today != today:
                report = build_daily_report()
                await send_to_owner(app, report)
                sent_today = today

        await asyncio.sleep(30)


async def range_monitor_loop(app):
    while True:
        pools = get_all()

        for pool in pools:
            pool, analysis = analyze_pool(pool)
            alerts, updated_pool = check_alerts(pool, analysis)

            update(updated_pool)

            for alert in alerts:
                await send_to_owner(app, alert)

        await asyncio.sleep(300)


async def start_background_tasks(app):
    asyncio.create_task(daily_report_loop(app))
    asyncio.create_task(range_monitor_loop(app))
