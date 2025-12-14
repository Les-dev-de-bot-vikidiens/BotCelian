import pywikibot
import sys

def confirmer(prompt):
    reponse = input(prompt + " (oui/non) : ").strip().lower()
    return reponse in ["oui", "o", "yes", "y"]

def main():
    site = pywikibot.Site("fr", "vikidia")
    site.login()

    print("=== Script de révocation manuelle des contributions d’un utilisateur ===")

    cible = input("Nom d'utilisateur à cibler : ").strip()

    if not confirmer(f"Es-tu sûr de vouloir annuler toutes les modifications de {cible} ?"):
        print("❌ Action annulée.")
        sys.exit()

    raison = input("Quelle est la raison de cette révocation ? ").strip()
    if not raison:
        raison = "Révocation manuelle (raison non précisée)"

    contribs = list(site.usercontribs(user=cible, total=500))
    nb_modifs = len(contribs)

    if nb_modifs == 0:
        print(f"ℹ️ Aucune contribution trouvée pour {cible}.")
        return

    if not confirmer(f"{cible} a {nb_modifs} contributions. Confirmer la révocation ?"):
        print("❌ Révocation annulée.")
        sys.exit()

    print(f"🔍 Analyse de {nb_modifs} contributions...")

    for contrib in contribs:
        titre = contrib['title']
        page = pywikibot.Page(site, titre)

        try:
            # Recharge proprement la page
            page = pywikibot.Page(site, page.title())
            page.get(force=True)

            # Vérifie que la dernière modification vient bien de l'utilisateur ciblé
            latest_rev = page.latest_revision
            if latest_rev.user != cible:
                print(f"[SKIP] {titre} : dernière modif par {latest_rev.user}, pas {cible}")
                continue

            # Obtenir les 2 dernières versions de la page
            history = list(page.revisions(total=2))
            if len(history) < 2:
                print(f"[SKIP] {titre} : pas de version précédente à restaurer")
                continue

            old_rev = history[1]
            old_text = page.getOldVersion(old_rev.revid)

            # Rafraîchir le token (contournement du bug token)
            site.tokens.clear()
            site.tokens.get('csrf')

            # Réécrit l'ancienne version de la page
            page.text = old_text
            page.save(
                summary=f"Révocation manuelle de la modification de {cible} : {raison}",
                minor=False
            )
            print(f"[OK] {titre} restaurée avec succès")

        except Exception as e:
            print(f"[ERREUR] {titre} : {e}")

    print("✅ Révocations terminées.")

if __name__ == "__main__":
    main()
