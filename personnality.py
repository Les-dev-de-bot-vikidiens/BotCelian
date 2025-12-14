#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot Vikidia – Catégorisation par genre via SPARQL direct
- QID Wikidata récupéré directement via SPARQL en recherchant le label
- Ajoute uniquement la catégorie Vikidia correspondante
"""

import pywikibot
from pywikibot import pagegenerators
import requests
import time

VIKIDIA = pywikibot.Site("fr", "vikidia")

CAT_SOURCE = "Catégorie:Personnalité par ordre alphabétique"
CAT_MALE = "Catégorie:Personnalité masculine par ordre alphabétique"
CAT_FEMALE = "Catégorie:Personnalité féminine par ordre alphabétique"

SUMMARY = (
    "Bot : Correction de [[Catégorie:Personnalité par ordre alphabétique]] par genre via Wikidata SPARQL "
)

Q_MALE = "Q6581097"
Q_FEMALE = "Q6581072"

SPARQL_ENDPOINT = "https://query.wikidata.org/sparql"
HEADERS = {
    "User-Agent": "BotCelian/VikidiaBot"
}

def sparql_query(query):
    try:
        r = requests.get(SPARQL_ENDPOINT, params={"query": query, "format": "json"}, headers=HEADERS, timeout=30)
        r.raise_for_status()
        return r.json()["results"]["bindings"]
    except Exception as e:
        print("Erreur SPARQL:", e)
        return []

def get_qid_from_label(label):
    query = f"""
    SELECT ?item WHERE {{
      ?item rdfs:label "{label}"@fr ;
            wdt:P31 wd:Q5 .
    }}
    LIMIT 1
    """
    results = sparql_query(query)
    if not results:
        return None
    return results[0]["item"]["value"].split("/")[-1]

def get_gender_via_qid(qid):
    query = f"""
    SELECT ?gender WHERE {{
      wd:{qid} wdt:P21 ?gender .
    }}
    LIMIT 1
    """
    results = sparql_query(query)
    if not results:
        return None
    gender_qid = results[0]["gender"]["value"].split("/")[-1]
    if gender_qid == Q_MALE:
        return "male"
    if gender_qid == Q_FEMALE:
        return "female"
    return None

def process_page(page, dry_run=True):
    title = page.title()
    print("\n=== Page Vikidia:", title, "===")

    qid = get_qid_from_label(title)
    if not qid:
        print("  Pas de QID trouvé sur Wikidata")
        return

    print("  QID Wikidata:", qid)

    gender = get_gender_via_qid(qid)
    if not gender:
        print("  Pas de genre reconnu")
        return

    print("  Genre détecté:", gender)

    # Ajout de la catégorie
    text = page.text
    changed = False

    if gender == "male" and CAT_MALE not in text:
        text += f"\n[[{CAT_MALE}]]"
        changed = True
    elif gender == "female" and CAT_FEMALE not in text:
        text += f"\n[[{CAT_FEMALE}]]"
        changed = True

    if changed:
        text = text.replace(f"[[{CAT_SOURCE}]]", "").strip()
        page.text = text
        if dry_run:
            print(f"  [DRY-RUN] Catégorie à ajouter: {CAT_MALE if gender=='male' else CAT_FEMALE}")
        else:
            page.save(SUMMARY)
            print("  Catégorie ajoutée !")
    else:
        print("  Pas de modification nécessaire")

    # Rate-limit: 1 page / seconde
    time.sleep(0.5)

def main(dry_run=True):
    category = pywikibot.Category(VIKIDIA, CAT_SOURCE)
    generator = pagegenerators.CategorizedPageGenerator(category)

    count = 0
    for page in generator:
        try:
            process_page(page, dry_run=dry_run)
            count += 1
        except Exception as e:
            pywikibot.error(f"Erreur sur {page.title()}: {e}")

    print(f"\nTotal de pages traitées: {count}")

if __name__ == "__main__":
    main(dry_run=False)  # dry_run=True → n’écrit rien, juste diagnostic

