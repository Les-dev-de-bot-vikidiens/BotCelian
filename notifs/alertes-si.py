import os
import pywikibot
import requests

# Configuration 
NTFY_TOPIC = "vikidia-si"
NTFY_URL = f"https://ntfy.sh/{NTFY_TOPIC}"

# Fichier local pour stocker les pages déjà notifiées
HISTORY_FILE = "notified_pages.txt"

def load_notified_pages():
    """Charge la liste des pages déjà notifiés depuis le fichier texte."""
    if not os.path.exists(HISTORY_FILE):
        return set()
    with open(HISTORY_FILE, "r", encoding="utf-8") as f:
        return set(line.strip() for line in f if line.strip())

def save_notified_pages(pages_set):
    """Sauvegarde la liste des pages."""
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        for title in pages_set:
            f.write(f"{title}\n")

def check_si_category():
    # Initialisation
    site = pywikibot.Site('fr', 'vikidia')
    
    # catégorie SI
    category = pywikibot.Category(site, 'Catégorie:Suppression immédiate')
    
    # Récupération des pages en SI
    current_items = list(category.members())
    
    if not current_items:
        # Si la catégorie est vide, on réinitialise l'historique
        if os.path.exists(HISTORY_FILE):
            os.remove(HISTORY_FILE)
        return

    # Chargement de l'historique
    already_notified = load_notified_pages()
    
    # Recherche des pages pas encore notifiés 
    new_items = [page for page in current_items if page.title() not in already_notified]

    if not new_items:
        return  # Aucun nouvel article à notifier

    total_si_count = len(current_items)

    # Traitement des nouveaux articles un par un
    for page in new_items:
        title = page.title()
        
        # Lien vers l'article
        url = page.full_url()
        
        # Calcul du nombre d'autres pages actuellement en SI
        other_pages_count = total_si_count - 1

        # Message
        message = (
            f"L'article : {title} a été mis en SI\n"
            f"{url}\n"
            f"Il y a {other_pages_count} autres pages en SI"
        )

        title_msg = f"{title}"

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
            pywikibot.output(f"Notification envoyée pour")
            
            # Ajout à l'historique
            already_notified.add(title)

        except Exception as e:
            pywikibot.error(f"Erreur lors de l'envoi de la notification pour {title} : {e}")

    # Enregistrement de l'historique
    save_notified_pages(already_notified)

if __name__ == "__main__":
    check_si_category()
