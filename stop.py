#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import urllib.parse
from datetime import datetime, timedelta, timezone
import requests

os.environ["HOME"] = "/home/celian"
os.environ["PYWIKIBOT_DIR"] = "/home/celian/pywikibot"
os.environ["PYTHONIOENCODING"] = "utf-8"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir("/home/celian/pywikibot")
sys.path.append("/home/celian/pywikibot")

import hashlib
import pywikibot
import urllib.parse
from datetime import datetime
from config import DISCORD_WEBHOOK_SHUTDOWN, BOT_NAME
import psutil

# ---------------- CONFIG ----------------
BOT_USERNAME = "BotCélian"
PDD_TITLE = f"Discussion utilisateur:{BOT_USERNAME}"
LOG_PAGE_TITLE = f"Utilisateur:{BOT_USERNAME}/Logs/2025"
HASH_FILE = "/home/celian/.pdd_hash"

# ---------------- SITE ----------------
site = pywikibot.Site("fr", "vikidia")
site.login()

# ---------------- HASH ----------------
def read_last_hash():
    if os.path.exists(HASH_FILE):
        with open(HASH_FILE, "r") as f:
            return f.read().strip()
    return None

def save_hash(h):
    with open(HASH_FILE, "w") as f:
        f.write(h)

def get_page_hash(page_title):
    page = pywikibot.Page(site, page_title)
    return hashlib.sha256(page.text.encode("utf-8")).hexdigest()

# ---------------- PDD ----------------
def get_last_user():
    try:
        page = pywikibot.Page(site, PDD_TITLE)
        if not page.exists():
            return None, None
        last_rev = next(page.revisions(total=1))
        return last_rev.user, hashlib.sha256(page.text.encode("utf-8")).hexdigest()
    except Exception as e:
        print(f"Erreur en vérifiant la PDD : {e}")
        return None, None

def reply_on_pdd(user):
    try:
        page = pywikibot.Page(site, PDD_TITLE)
        response_template = f"{{{{ping|{user}}}}} L’utilisateur '''{user}''' a demandé l’arrêt du bot. Le bot s'est arrêté correctement. <sup> Message automatisé </sup> ~~~~"
        page.text += "\n\n" + response_template
        page.save(summary="Réponse automatique suite à l'arrêt d'urgence", minor=True, bot=False)
        print(f"✅ Réponse envoyée à {user} sur la PDD.")
    except Exception as e:
        print(f"Erreur en postant la réponse sur la PDD : {e}")

# ---------------- LOG PAGE ----------------
def log_shutdown_event(user, pages_analysed=0, total_changes=0, duration="0s"):
    try:
        page = pywikibot.Page(site, LOG_PAGE_TITLE)
        old_text = page.text if page.exists() else ""
        now = datetime.now()
        today_fr = now.strftime("%d/%m/%Y")
        heure_fr = now.strftime("%H:%M:%S")
        new_entry = f"""{{{{Utilisateur:BotCélian/Resume
| script = stop
| date = {today_fr}
| heure = {heure_fr}
| durée = {duration}
| analyse = action demandé par {user}
| modifs =
}}}}"""
        page.text = (old_text + "\n" + new_entry).strip()
        page.save(summary=f"Log shutdown automatique suite à message de {user}", minor=True)
        print(f"✅ Log shutdown mis à jour pour {user}")
    except Exception as e:
        print(f"Erreur en mettant à jour la page de logs : {e}")

# ---------------- DISCORD ----------------
def send_discord_embed(user):
    try:
        page_url = urllib.parse.quote(PDD_TITLE.replace(" ", "_"))
        wiki_link = f"https://fr.vikidia.org/wiki/{page_url}"
        embed = {
            "title": f"⚠️ Arrêt de {BOT_USERNAME}",
            "description": f"L’utilisateur **{user}** a demandé l’arrêt du bot.\n[PDD]({wiki_link})",
            "color": 0xFF0000
        }
        payload = {"username": BOT_NAME, "embeds": [embed]}
        requests.post(DISCORD_WEBHOOK_SHUTDOWN, json=payload, timeout=10)
        print("✅ Embed Discord envoyé")
    except Exception as e:
        print(f"Erreur en envoyant l'embed Discord : {e}")

# ---------------- MAIN ----------------
def main():
    print("Vérification PDD pour arrêt demandé...")
    user, current_hash = get_last_user()
    if not user:
        print("Aucun message détecté sur la PDD. Aucun arrêt.")
        return

    last_hash = read_last_hash()
    if last_hash != current_hash:
        print(f"Arrêt demandé par {user}. Exécution du shutdown...")
        reply_on_pdd(user)
        save_hash(current_hash)
        log_shutdown_event(user)
        send_discord_embed(user)
        os.system("sudo shutdown -h now")
    else:
        print("Aucune modification de la PDD détectée. Tout va bien.")
        save_hash(current_hash)

if __name__ == "__main__":
    main()
