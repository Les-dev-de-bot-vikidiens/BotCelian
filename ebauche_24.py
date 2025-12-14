import pywikibot
import re
import mwparserfromhell
from datetime import datetime, timedelta

LOG_FILE = "ebauche_scan_once_log.txt"

def log(message):
    timestamp = datetime.utcnow().strftime("[%Y-%m-%d %H:%M:%S UTC] ")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(timestamp + message + "\n")
    print(timestamp + message)

def extract_portails(text):
    try:
        wikicode = mwparserfromhell.parse(text)
        for template in wikicode.filter_templates():
            if template.name.strip().lower() == "portail":
                return [param.value.strip().lower() for param in template.params if param.value.strip()]
    except Exception:
        raise ValueError("Texte illisible ou mal formé")
    return []

def normalize_ebauche_portails(site, portails):
    valid_portails = []
    for p in portails:
        titre1 = f"Modèle:Ébauche {p}"
        titre2 = f"Modèle:Ébauche {p.capitalize()}"
        if pywikibot.Page(site, titre1).exists():
            valid_portails.append(p)
        elif pywikibot.Page(site, titre2).exists():
            valid_portails.append(p.capitalize())
    return valid_portails

def has_ebauche(text):
    return re.search(r'\{\{\s*ébauche(?:\s*[\|\s][^}]*)?\}\}', text, re.IGNORECASE)

def has_travaux(text):
    return re.search(r'\{\{\s*(en\s+)?travaux(?:\s*\|[^}]+)?\s*\}\}', text, re.IGNORECASE)

def normalize_ebauche_portails(site, portails):
    valid_portails = []
    for p in portails:
        titre1 = f"Modèle:Ébauche {p}"
        titre2 = f"Modèle:Ébauche {p.capitalize()}"
        if pywikibot.Page(site, titre1).exists():
            valid_portails.append(p)
        elif pywikibot.Page(site, titre2).exists():
            valid_portails.append(p.capitalize())
    return valid_portails

def add_ebauche(text, portails):
    if not portails:
        return text
    ebauche_template = "{{ébauche|" + "|".join(portails) + "}}\n"
    return ebauche_template + text

def is_too_short(text, min_words=200):
    return len(text.split()) < min_words

def main():
    site = pywikibot.Site("fr", "vikidia")
    site.login()

    since = datetime.utcnow() - timedelta(days=1)
    recent_newpages = site.recentchanges(start=since, changetype="new", namespaces=[0], reverse=True)

    for change in recent_newpages:
        title = change['title']
        page = pywikibot.Page(site, title)

        if page.isRedirectPage():
            continue

        try:
            text = page.text
        except Exception as e:
            log(f"{page.title()} ignorée : erreur de lecture → {e}")
            continue

        if not is_too_short(text):
            continue

        if has_ebauche(text):
            log(f"{page.title()} ignorée : ébauche déjà présente")
            continue

        if has_travaux(text):
            log(f"{page.title()} ignorée : modèle {{Travaux}} ou {{En travaux}} présent")
            continue


        try:
            portails = extract_portails(text)
        except ValueError:
            log(f"{page.title()} ignorée : contenu illisible ou anomalie de parsing")
            continue

        if not portails:
            log(f"{page.title()} ignorée : aucun portail détecté (à ajouter manuellement)")
            continue

        portails = normalize_ebauche_portails(site, portails)
        if not portails:
            log(f"{page.title()} ignorée : aucun modèle ébauche valide trouvé")
            continue
        new_text = add_ebauche(text, portails)


        try:
            page.text = new_text
            page.save(summary="Ajout automatique du modèle ébauche")
            log(f"Ajout de l’ébauche sur la page {page.title()}")
            #break  # Ne modifie qu’une page
        except Exception as e:
            log(f"Erreur lors de la sauvegarde de {page.title()} : {e}")
            continue

    log("Scan terminé.\n")

if __name__ == "__main__":
    main()