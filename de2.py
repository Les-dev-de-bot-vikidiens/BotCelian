import pywikibot
import time
import re

site = pywikibot.Site()
site.login()

SOURCE = "Personnalité par ordre alphabétique"
MALE = "Personnalité masculine par ordre alphabétique"
FEMALE = "Personnalité féminine par ordre alphabétique"

cat = pywikibot.Category(site, "Catégorie:" + SOURCE)

def has_gender_cat(text):
    return (
        re.search(r"\[\[\s*Catégorie\s*:\s*" + MALE, text, re.I)
        or re.search(r"\[\[\s*Catégorie\s*:\s*" + FEMALE, text, re.I)
    )

def remove_source_cat(text):
    return re.sub(
        r"\[\[\s*Catégorie\s*:\s*" + SOURCE + r"(?:\|.*?)?\s*\]\]\s*",
        "",
        text,
        flags=re.IGNORECASE
    )

for page in cat.members(namespaces=[0]):
    try:
        print("\n→", page.title())
        text = page.get()

        if not has_gender_cat(text):
            print("  ⛔ pas de catégorie masculine/féminine")
            continue

        if not re.search(r"\[\[\s*Catégorie\s*:\s*" + SOURCE, text, re.I):
            print("  ⛔ catégorie source déjà absente")
            continue

        new_text = remove_source_cat(text)

        if new_text == text:
            print("  ⛔ regex n’a rien modifié")
            continue

        page.put(
            new_text,
            summary="Suppression de la catégorie redondante « Personnalité par ordre alphabétique »",
            minor=True
        )

        print("  ✅ catégorie supprimée")
        time.sleep(1)

    except Exception as e:
        print("❌ ERREUR :", e)
        time.sleep(1)
