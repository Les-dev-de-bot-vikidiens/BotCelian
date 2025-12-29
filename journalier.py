# Les  DISCORD_WEBHOOK_STATS, BOT_NAME sont défnis dans un fichier config.py

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import requests
from collections import Counter

# ================= ENV CRON (spécifique à la config pour BotCélian) =================
os.environ["HOME"] = "/home/celian"
os.environ["PYWIKIBOT_DIR"] = "/home/celian/pywikibot"

sys.path.append("/home/celian/pywikibot")
os.chdir("/home/celian/pywikibot")

# ================= PYWIKIBOT =================
import pywikibot
from pywikibot.data.api import Request

site = pywikibot.Site("fr", "vikidia")
site.login()

# ================= CONFIG =================
from config import DISCORD_WEBHOOK_STATS, BOT_NAME

PARIS_TZ = ZoneInfo("Europe/Paris")

# ================= DISCORD =================
def send_discord_embed(stats, start_dt, end_dt):
    embed = {
        "title": "📊 Statistiques journalières Vikidia",
        "description": (
            f"Période analysée :\n"
            f"🕕 **{start_dt.strftime('%d/%m %H:%M')} → "
            f"{end_dt.strftime('%d/%m %H:%M')}**"
        ),
        "color": 0xE67E22,
        "fields": [
            {
                "name": "🕒 Activité horaire",
                "value": (
                    f"Heure pleine : **{stats['peak_hour']}h** "
                    f"({stats['peak_count']} modifs)\n"
                    f"Heure creuse : **{stats['low_hour']}h** "
                    f"({stats['low_count']} modifs)"
                ),
                "inline": False
            },
            {
                "name": "🆕 Création & édition",
                "value": (
                    f"🆕 Pages créées : **{stats['pages_created']}**\n"
                    f"✏️ Pages modifiées : **{stats['pages_edited']}**"
                ),
                "inline": False
            },
            {
                "name": "🔥 Article le plus modifié",
                "value": f"**{stats['hot_article']}** ({stats['hot_count']} modifs)",
                "inline": False
            },
            {
                "name": "🚨 Modération",
                "value": (
                    f"🗑️ Pages supprimées : **{stats['deleted_pages']}**\n"
                    f"🔒 Utilisateurs bloqués : **{stats['blocked_users']}**"
                ),
                "inline": False
            }
        ],
        "footer": {"text": BOT_NAME}
    }

    requests.post(
        DISCORD_WEBHOOK_STATS,
        json={"embeds": [embed]},
        timeout=10
    )

# ================= STATS =================
def get_stats(site, start_utc, end_utc):

    rc_params = {
        "action": "query",
        "list": "recentchanges",
        "rctype": ["edit", "new"],
        "rcnamespace": [0],
        "rcstart": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rcend": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rclimit": "500",
        "rcprop": "title|timestamp"
    }

    rc_data = Request(site=site, parameters=rc_params).submit()
    changes = rc_data["query"]["recentchanges"]

    hour_counter = Counter({h: 0 for h in range(24)})
    page_counter = Counter()

    pages_created = 0
    pages_edited = 0

    for change in changes:
        ts_utc = datetime.fromisoformat(change["timestamp"].replace("Z", "+00:00"))
        ts_fr = ts_utc.astimezone(PARIS_TZ)

        hour_counter[ts_fr.hour] += 1
        page_counter[change["title"]] += 1

        if change["type"] == "new":
            pages_created += 1
        elif change["type"] == "edit":
            pages_edited += 1

    peak_hour, peak_count = hour_counter.most_common(1)[0]
    low_hour, low_count = min(hour_counter.items(), key=lambda x: x[1])

    hot_article, hot_count = page_counter.most_common(1)[0]

    # ---------- Pages supprimées ----------
    delete_data = Request(
        site=site,
        parameters={
            "action": "query",
            "list": "logevents",
            "letype": "delete",
            "lestart": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "leend": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lelimit": "500"
        }
    ).submit()

    deleted_pages = len(delete_data["query"]["logevents"])

    # ---------- Utilisateurs bloqués ----------
    block_data = Request(
        site=site,
        parameters={
            "action": "query",
            "list": "logevents",
            "letype": "block",
            "lestart": end_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "leend": start_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "lelimit": "500"
        }
    ).submit()

    blocked_users = len(block_data["query"]["logevents"])

    return {
        "peak_hour": peak_hour,
        "peak_count": peak_count,
        "low_hour": low_hour,
        "low_count": low_count,
        "hot_article": hot_article,
        "hot_count": hot_count,
        "pages_created": pages_created,
        "pages_edited": pages_edited,
        "deleted_pages": deleted_pages,
        "blocked_users": blocked_users
    }

# ================= MAIN =================
def main():
    now_utc = datetime.now(timezone.utc)
    start_utc = (now_utc - timedelta(days=1)).replace(
        hour=18, minute=0, second=0, microsecond=0
    )

    stats = get_stats(site, start_utc, now_utc)

    send_discord_embed(
        stats,
        start_utc.astimezone(PARIS_TZ),
        now_utc.astimezone(PARIS_TZ)
    )

if __name__ == "__main__":
    main()
