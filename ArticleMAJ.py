#!/usr/bin/python3
# -*- coding: utf-8 -*-

import pywikibot
import re

PAGE_TITLE = "Vikidia:Articles importants et courts"
MAX_SIZE = 1400  # taille limite

def main():
    site = pywikibot.Site("fr", "vikidia")
    page = pywikibot.Page(site, PAGE_TITLE)

    full_text = page.get()

    # Délimitation de la zone à vérifier
    start_marker = "== Articles classés =="
    end_marker = "== Source de la liste =="

    start_index = full_text.find(start_marker)
    end_index = full_text.find(end_marker)

    if start_index == -1 or end_index == -1:
        print("Impossible de trouver la zone Articles classés.")
        return

    before = full_text[:start_index]
    section = full_text[start_index:end_index]
    after = full_text[end_index:]

    matches = re.findall(r"\{\{Wpj\|(.*?)\}\}", section)
    print(f"{len(matches)} modèles {{Wpj|...}} trouvés.")

    to_remove = []

    for title in matches:
        article = pywikibot.Page(site, title)

        try:
            size = article.latest_revision.size
        except:
            print(f"Impossible de lire : {title}")
            continue

        print(f"→ {title} : {size} octets")

        if size > MAX_SIZE:
            to_remove.append(title)

    print(f"{len(to_remove)} articles dépassent {MAX_SIZE} octets.")

    # --- Suppression des lignes contenant {{Wpj|Titre}}
    new_section = section
    for title in to_remove:
        pattern = r".*?\{\{Wpj\|" + re.escape(title) + r"\}\}.*\n"
        new_section = re.sub(pattern, "", new_section)

    # Reconstruction de la page complète
    new_text = before + new_section + after

    if new_text != full_text:
        page.text = new_text
        page.save(summary="Retrait automatique des articles de plus de 1400 octets")
        print("Page mise à jour.")
    else:
        print("Aucun changement à enregistrer.")

if __name__ == "__main__":
    main()

