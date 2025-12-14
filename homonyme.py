
# le script sert à supprimer les portails des pages d'homonymies de Vikidia
import pywikibot
import mwparserfromhell

def has_homonymie(wikicode):
    for template in wikicode.filter_templates():
        if template.name.strip().lower() == "homonymie":
            return True
    return False

def remove_portail_templates(wikicode):
    to_remove = []
    for template in wikicode.filter_templates():
        if template.name.strip().lower() == "portail":
            to_remove.append(template)
    for t in to_remove:
        wikicode.remove(t)
    return len(to_remove) > 0

def main():
    site = pywikibot.Site("fr", "vikidia")
    site.login()

    for page in site.allpages(namespace=0):
        if page.isRedirectPage():
            continue

        try:
            text = page.text
            wikicode = mwparserfromhell.parse(text)
        except Exception as e:
            print(f"Erreur de lecture de {page.title()} : {e}")
            continue

        if not has_homonymie(wikicode):
            continue

        if remove_portail_templates(wikicode):
            print(f"Suppression des portails sur {page.title()}")
            page.text = str(wikicode)
            try:
                page.save(summary="Retrait du modèle Portail sur page d’homonymie", minor=True)
            except Exception as e:
                print(f"Erreur lors de la sauvegarde de {page.title()} : {e}")

if __name__ == "__main__":
    main()
