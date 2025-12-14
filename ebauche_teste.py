import pywikibot
import re
import mwparserfromhell
from pywikibot import pagegenerators
from datetime import datetime

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
                return [param.value.strip().lower() for param in template.params]
    except Exception as e:
        raise ValueError("Texte mal formé")
    return []

def has_ebauche(text):
    # Ignore aussi les variantes comme {{ébauche exemple}} sans "|"
    return re.search(r'\{\{\s*ébauche(\s*[\|\s][^}]*)?\}\}', text, re.IGNORECASE)

def add_ebauche(text, portails):
    if not portails:
        return text
    ebauche_template = '{{ébauche|' + '|'.join(portails) + '}}\n'
    return ebauche_template + text

def is_too_short(text, min_words=200):
    return len(text.split()) < min_words

def main():
    site = pywikibot.Site("fr", "vikidia")
    site.login()

    gen = pagegenerators.AllpagesPageGenerator(namespace=0, site=site)

    for page in gen:
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

        try:
            portails = extract_portails(text)
        except ValueError:
            log(f"{page.title()} ignorée : texte malformé")
            continue

        if not portails:
            log(f"{page.title()} ignorée : aucun portail trouvé")
            continue

        new_text = add_ebauche(text, portails)

        try:
            page.text = new_text
            page.save(summary="Ajout automatique du modèle ébauche")
            log(f"Ajout de l’ébauche sur : {page.title()}")
            break  # S’arrête après une modification
        except Exception as e:
            log(f"Erreur lors de la sauvegarde de {page.title()} : {e}")
            continue

    log("Scan terminé.\n")

if __name__ == "__main__":
    main()
