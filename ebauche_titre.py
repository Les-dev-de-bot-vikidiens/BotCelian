import pywikibot
import re
import mwparserfromhell
from datetime import datetime

LOG_FILE = "ebauche_par_titre_log.txt"

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
    except Exception:
        raise ValueError("Texte mal formé")
    return []

def has_ebauche(text):
    return re.search(r'\{\{\s*ébauche(\s*[\|\s][^}]*)?\}\}', text, re.IGNORECASE)

def add_ebauche(text, portails):
    if not portails:
        return text
    ebauche_template = '{{ébauche|' + '|'.join(portails) + '}}\n'
    return ebauche_template + text

def is_too_short(text, min_words=200):
    return len(text.split()) < min_words

def traiter_page(titre):
    site = pywikibot.Site("fr", "vikidia")
    site.login()

    page = pywikibot.Page(site, titre)

    if page.isRedirectPage():
        log(f"{titre} ignorée : redirection")
        return

    try:
        text = page.text
    except Exception as e:
        log(f"{titre} ignorée : erreur de lecture → {e}")
        return

    if not is_too_short(text):
        log(f"{titre} ignorée : texte assez long")
        return

    if has_ebauche(text):
        log(f"{titre} ignorée : ébauche déjà présente")
        return

    try:
        portails = extract_portails(text)
    except ValueError:
        log(f"{titre} ignorée : texte malformé")
        return

    if not portails:
        log(f"{titre} ignorée : aucun portail trouvé")
        return

    new_text = add_ebauche(text, portails)

    try:
        page.text = new_text
        page.save(summary="Ajout automatique du modèle ébauche")
        log(f"Ajout de l’ébauche sur : {titre}")
    except Exception as e:
        log(f"Erreur lors de la sauvegarde de {titre} : {e}")

def main():
    titres = input("Entre un ou plusieurs titres de pages (séparés par des virgules) : ")
    titres = [t.strip() for t in titres.split(',')]
    for titre in titres:
        traiter_page(titre)

if __name__ == "__main__":
    main()
