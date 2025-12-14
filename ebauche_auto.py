import pywikibot
import re
from datetime import datetime, timedelta
from pywikibot.data.api import Request

LOG_FILE = "ebauche_log.txt"

def log(message):
    timestamp = datetime.utcnow().strftime("[%Y-%m-%d %H:%M:%S UTC] ")
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(timestamp + message + "\n")
    print(timestamp + message)

def extract_portails(text):
    match = re.search(r'\{\{\s*[Pp]ortail\s*\|([^}]+)\}\}', text)
    if not match:
        return []
    return [param.strip().lower() for param in match.group(1).split('|')]

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
    return re.search(r'\{\{\s*ébauche\s*(\|[^}]*)?\}\}', text, re.IGNORECASE)

def has_Ebauche(text):
    return re.search(r'\{\{\s*Ébauche\s*(\|[^}]*)?\}\}', text, re.IGNORECASE)

def has_travaux(text):
    return re.search(r'\{\{\s*(en\s+)?travaux(?:\s*\|[^}]+)?\s*\}\}', text, re.IGNORECASE)

def add_ebauche(text, portails):
    if not portails:
        return text
    ebauche_template = '{{ébauche|' + '|'.join(portails) + '}}\n'
    return ebauche_template + text

def is_too_short(text, min_words=200):
    return len(text.split()) < min_words

def get_new_pages(site):
    # Récupère les pages créées dans les dernières 24 heures
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)

    log("Récupération des nouvelles pages créées entre "
        f"{yesterday.isoformat()} et {now.isoformat()}")

    params = {
        "action": "query",
        "list": "recentchanges",
        "rcnamespace": 0,
        "rcshow": "new",
        "rclimit": "max",
        "rcstart": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rcend": yesterday.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rcprop": "title"
    }

    request = Request(site=site, parameters=params)
    data = request.submit()
    titles = [change["title"] for change in data["query"]["recentchanges"]]
    return [pywikibot.Page(site, title) for title in titles]

def main():
    site = pywikibot.Site("fr", "vikidia")
    site.login()

    pages = get_new_pages(site)
    log(f"{len(pages)} nouvelles pages détectées.")

    for page in pages:
        try:
            if page.isRedirectPage():
                log(f"{page.title()} est une redirection. Ignorée.")
                continue

            text = page.text

            if not is_too_short(text):
                log(f"{page.title()} n’est pas trop courte.")
                continue

            if has_ebauche(text):
                log(f"{page.title()} contient déjà une ébauche.")
                continue

            if has_Ebauche(text):
                log(f"{page.title()} contient déjà une ébauche.")
                continue

            if has_travaux(text):
                log(f"{page.title()} ignorée : modèle {{Travaux}} ou {{En travaux}} présent")
                continue

            portails = extract_portails(text)
            if not portails:
                log(f"{page.title()} : aucun portail trouvé.")
                continue

            portails = normalize_ebauche_portails(site, portails)
            if not portails:
                log(f"{page.title()} ignorée : aucun modèle ébauche valide trouvé")
                continue

            new_text = add_ebauche(text, portails)
            page.text = new_text
            page.save(summary="Ajout automatique du modèle ébauche")
            log(f"Ajout de l’ébauche sur : {page.title()}")

        except Exception as e:
            log(f"Erreur avec {page.title()} : {e}")

    log("Scan terminé.\n")

if __name__ == "__main__":
    main()
