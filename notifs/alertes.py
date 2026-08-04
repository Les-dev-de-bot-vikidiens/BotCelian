import os
import re
import urllib.parse
import pywikibot
import requests

# Configuration
NTFY_TOPIC = "vikidia-alerte"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

PAGE_NAME = "Vikidia:Alerte/28"
REV_HISTORY_FILE = "alert.log"

def load_last_revid():
    if os.path.exists(REV_HISTORY_FILE):
        with open(REV_HISTORY_FILE, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if content.isdigit():
                return int(content)
    return None

def save_last_revid(revid):
    """Sauvegarde l'ID de la dernière modifs."""
    with open(REV_HISTORY_FILE, "w", encoding="utf-8") as f:
        f.write(str(revid))

def extract_target_user(wikitext):
    #Extrait le nom d'utilisateur ou l'IP
    # Cherche la dernière occurrence d'un titre "Demande de blocage de ..."
    pattern = r"==\s*Demande de blocage de\s+(.*?)\s*=="
    matches = re.findall(pattern, wikitext, re.IGNORECASE)
    
    if not matches:
        return "Inconnu"

    raw_target = matches[-1].strip()

    # Nettoyage des modèles
    # 1. Cas des modèles
    template_match = re.search(r"\{\{[^|}]*\|([^}]+)\}\}", raw_target)
    if template_match:
        return template_match.group(1).strip()

    # 2. Cas des liens internes
    link_match = re.search(r"\[\[(?:[^|\]]*\|)?([^\]]+)\]\]", raw_target)
    if link_match:
        return link_match.group(1).strip()

    # 3. Texte brut
    return raw_target

def check_alerte_page():
    site = pywikibot.Site('fr', 'vikidia')
    page = pywikibot.Page(site, PAGE_NAME)

    if not page.exists():
        pywikibot.output(f"La page {PAGE_NAME} n'existe pas.")
        return

    latest_rev = page.latest_revision
    last_processed_revid = load_last_revid()

    # Si aucune modification n'a eu lieu depuis la dernière exécution, on arrête
    if last_processed_revid == latest_rev.revid:
        return

    # /\
    if last_processed_revid is None:
        save_last_revid(latest_rev.revid)
        return

    editor_username = latest_rev.user
    editor_user = pywikibot.User(site, editor_username)

    save_last_revid(latest_rev.revid)

    # Vérification que c'est pas un admin
    if "sysop" in editor_user.groups():
        pywikibot.output(f"Modification ignorée (administrateur : {editor_username}).")
        return

    # demande
    target_user = extract_target_user(page.text)

    # Création lien vers les contribs de l'utilisateur
    encoded_target = urllib.parse.quote(target_user)
    contribs_link = f"https://fr.vikidia.org/wiki/Sp%C3%A9cial:Contributions/{encoded_target}"

    # Message
    message = f"{editor_username} a demandé un blocage de {target_user}\n{contribs_link}"
    title_msg = f"Vikidia : Demande de blocage"

    # Envoi de la notification ntfy
    try:
        response = requests.post(
            NTFY_URL,
            data=message.encode('utf-8'),
            headers={
                "Title": title_msg,
                "Priority": "default",
                "Tags": "warning,vikidia"
            }
        )
        response.raise_for_status()
        pywikibot.output(f"Notification envoyée")
    except Exception as e:
        pywikibot.error(f"Erreur lors de l'envoi de la notification ntfy : {e}")

if __name__ == "__main__":
    check_alerte_page()
