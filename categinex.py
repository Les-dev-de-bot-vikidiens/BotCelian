import pywikibot
import requests
import threading
import time
import os

FICHIER_PAGES_TRAITEES = "pages_traitees.txt"

# Lancer le thread en arrière-plan
threading.Thread(target=envoyer_ping, daemon=True).start()

# Connexion au site Vikidia
site = pywikibot.Site("fr", "vikidia")

def charger_pages_traitees():
    """Charge la liste des pages déjà traitées à partir du fichier."""
    if os.path.exists(FICHIER_PAGES_TRAITEES):
        with open(FICHIER_PAGES_TRAITEES, "r", encoding="utf-8") as f:
            return set(f.read().splitlines())
    return set()

def enregistrer_page_traitee(page_title):
    """Ajoute une page traitée au fichier."""
    with open(FICHIER_PAGES_TRAITEES, "a", encoding="utf-8") as f:
        f.write(page_title + "\n")

def supprimer_categories_inexistantes(page):
    """Supprime les catégories inexistantes d'une page."""
    if not page.exists():
        print(f"❌ La page '{page.title()}' n'existe pas.")
        return

    texte = page.text
    categories = page.categories()
    texte_modifie = texte
    categories_supprimees = []

    for cat in categories:
        if not cat.exists():
            cat_syntaxe = f"[[{cat.title()}]]"
            texte_modifie = texte_modifie.replace(cat_syntaxe, "")
            categories_supprimees.append(cat.title())

    if texte != texte_modifie:
        page.text = texte_modifie
        page.save(f"Suppression de catégories inexistantes : {', '.join(categories_supprimees)}")
        print(f"✅ Catégories supprimées sur '{page.title()}': {categories_supprimees}")
        enregistrer_page_traitee(page.title())
    else:
        print(f"⚠️ Aucune catégorie inexistante sur '{page.title()}'.")

def traiter_toutes_les_pages():
    """Parcourt toutes les pages de l'espace principal et supprime les catégories inexistantes si la page n'a pas encore été traitée."""
    pages_traitees = charger_pages_traitees()

    for page in site.allpages(namespace=0):
        if page.title() not in pages_traitees:
            supprimer_categories_inexistantes(page)
        else:
            print(f"🔄 Page '{page.title()}' déjà traitée, passage à la suivante.")

# Lancer le script
traiter_toutes_les_pages()