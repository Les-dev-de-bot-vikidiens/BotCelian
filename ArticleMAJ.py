#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Script généré par IA 
import os
import sys
import re
import time
from datetime import datetime, timezone
os.environ["PYWIKIBOT_DIR"] = "/app"
import pywikibot

# ================= CONFIG =================
PAGE_TITLE = "Vikidia:Articles importants et courts"
MAX_SIZE = 1400  # taille limite en octets
LOG_PAGE_TITLE = "Utilisateur:BotCélian/Logs/2026"

# ================= MAIN =================
def main():
    start_time = time.time()
    now = datetime.now(timezone.utc)
    today_fr = now.strftime("%d/%m/%Y")
    heure_fr = now.strftime("%H:%M:%S")

    site = pywikibot.Site("fr", "vikidia")
    site.login()

    page = pywikibot.Page(site, PAGE_TITLE)
    full_text = page.text

    # Délimitation de la zone à vérifier
    start_marker = "== Articles classés =="
    end_marker = "== Source de la liste =="

    start_index = full_text.find(start_marker)
    end_index = full_text.find(end_marker)

    if start_index == -1 or end_index == -1:
        print("❌ Impossible de trouver la zone Articles classés.")
        return

    before = full_text[:start_index]
    section = full_text[start_index:end_index]
    after = full_text[end_index:]

    matches = re.findall(r"\{\{Wpj\|(.*?)\}\}", section)
    print(f"🔍 {len(matches)} modèles {{Wpj|...}} trouvés.")

    to_remove = []
    for title in matches:
        article = pywikibot.Page(site, title)
        try:
            size = article.latest_revision.size
        except Exception as e:
            print(f"⚠️ Impossible de lire : {title} ({e})")
            continue

        print(f"→ {title} : {size} octets")
        if size > MAX_SIZE:
            to_remove.append(title)

    print(f"🧹 {len(to_remove)} articles dépassent {MAX_SIZE} octets.")

    # Suppression des lignes contenant {{Wpj|Titre}}
    new_section = section
    for title in to_remove:
        pattern = r".*?\{\{Wpj\|" + re.escape(title) + r"\}\}.*\n"
        new_section = re.sub(pattern, "", new_section)

    new_text = before + new_section + after

    if new_text != full_text:
        page.text = new_text
        page.save(summary=f"Retrait automatique des articles de plus de {MAX_SIZE} octets")
        print("✅ Page mise à jour.")
    else:
        print("ℹ️ Aucun changement à enregistrer.")

    # ================= RÉSUMÉ BOT =================
    duration = f"{int(time.time() - start_time)}s"
    log_page = pywikibot.Page(site, LOG_PAGE_TITLE)
    old_log = log_page.text if log_page.exists() else ""

    resume = f"""
{{{{Utilisateur:BotCélian/Resume
| script = articlemaj
| date = {today_fr}
| heure = {heure_fr}
| durée = {duration}
| analyse = {len(matches)}
| modifs = {len(to_remove)} articles enlevés 
}}}}
"""

    log_page.text = old_log.rstrip() + "\n\n" + resume.strip()
    log_page.save(
        summary="📊 BotCélian : résumé automatique du script ArticleMAJ",
        minor=True
    )

    print(f"✅ Résumé ajouté sur {LOG_PAGE_TITLE}")

# ================= ENTRY =================
if __name__ == "__main__":
    main()
