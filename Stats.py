import pywikibot
from datetime import datetime, timezone
import re
import sys
from collections import defaultdict

site = pywikibot.Site()
site.login()

# Date
now = datetime.now(timezone.utc)
today_iso = now.strftime("%Y-%m-%d")
today_fr = now.strftime("%d/%m/%Y")

# Pages de stats
page_stats_title = "Utilisateur:BotCélian/Stats"
page_archive_title = "Utilisateur:BotCélian/Stats/Archives"

# Récupérer les modifications récentes
rc_change = list(site.recentchanges(
    start=now.isoformat(),
    end=today_iso + "T00:00:00Z",
    namespaces=[0],
    changetype=None,
    total=500
))

# Liste des bots
bots = {user['name'] for user in site.allusers(group='bot')}
bots.add("BotCélian")

# Analyse des contributions
users = defaultdict(int)
pages = defaultdict(int)
new_articles = 0

for rc in rc_change:
    user = rc.get("user")
    if rc.get("bot") or user in bots:
        continue
    users[user] += 1
    pages[rc["title"]] += 1
    if rc["type"] == "new":
        new_articles += 1

total_changes = sum(users.values())

if total_changes == 0:
    print("Aucune modification trouvée (hors bots).")
    sys.exit(0)

# Générer le contenu des stats
top_users = sorted(users.items(), key=lambda x: x[1], reverse=True)
top_pages = sorted(pages.items(), key=lambda x: x[1], reverse=True)[:5]

section = f"== 📊 Statistiques du {today_fr} ==\n"
section += f"* 🔁 Modifications totales : '''{total_changes}'''\n"
section += f"* 🆕 Nouveaux articles : '''{new_articles}'''\n\n"

section += "'''🔝 Top 5 des pages les plus modifiées'''\n"
for i, (title, count) in enumerate(top_pages, 1):
    section += f"* {i}. [[{title}]] – {count} modif(s)\n"

section += "\n'''👥 Contributeurs les plus actifs'''\n"
for i, (user, count) in enumerate(top_users[:10], 1):
    section += f"* {i}. [[Utilisateur:{user}|{user}]] – {count} modif(s)\n"

# Mettre à jour la page principale de stats
page_stats = pywikibot.Page(site, page_stats_title)
page_stats.text = section
page_stats.save(summary=f"📊 MAJ automatique du {today_fr}")

# Mettre à jour les archives
page_archive = pywikibot.Page(site, page_archive_title)
old_archive = page_archive.text if page_archive.exists() else ""

# Nettoyer l'ancien sommaire
content_wo_sommaire = re.sub(
    r"^== Sommaire ==[\s\S]*?(?=\n== 📊|$)", "", old_archive, flags=re.MULTILINE
).strip()

# Remplacer ou ajouter la section du jour
section_regex = re.compile(
    rf"== 📊 Statistiques du {re.escape(today_fr)} ==[\s\S]*?(?=\n==|$)", re.MULTILINE
)

if section_regex.search(content_wo_sommaire):
    content_wo_sommaire = section_regex.sub(section.strip(), content_wo_sommaire)
else:
    content_wo_sommaire += "\n\n" + section.strip()

# Recréer le sommaire
section_titles = re.findall(
    r"== 📊 Statistiques du ([0-9]{2}/[0-9]{2}/[0-9]{4}) ==",
    content_wo_sommaire
)
sommaire = "== Sommaire ==\n" + "\n".join(
    f"* [[#📊 Statistiques du {date}]]" for date in section_titles
)

final_archive = f"{sommaire.strip()}\n\n{content_wo_sommaire.strip()}"
page_archive.text = final_archive
page_archive.save(summary=f"🗃️ MAJ archives  ({today_fr})")

print(f"✅ Statistiques mises à jour pour le {today_fr}")
