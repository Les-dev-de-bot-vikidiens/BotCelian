import pywikibot
import time
import re
from datetime import datetime, timedelta

site = pywikibot.Site()
site.login()

since = datetime.utcnow() - timedelta(days=7)

def split_text_ignoring_blocks(text):
    """
    Sépare le texte en segments :
    - à traiter (hors {{ }}, {| |}, <!-- -->, [ ])
    - à ignorer (dans ces blocs)
    Retourne une liste de tuples : (segment, à_corriger: True/False)
    """
    segments = []
    i = 0
    n = len(text)
    while i < n:
        # Bloc à ignorer : commentaire HTML
        if text[i:i+4] == '<!--':
            start = i
            i += 4
            while i < n and text[i-3:i+1] != '-->':
                i +=1
            segments.append((text[start:i], False))
            i +=1
        # Bloc à ignorer : modèle {{ }}
        elif text[i:i+2] == '{{':
            start = i
            depth = 2
            i += 2
            while i < n and depth > 0:
                if text[i:i+2] == '{{':
                    depth += 2
                    i +=2
                elif text[i:i+2] == '}}':
                    depth -=2
                    i +=2
                else:
                    i +=1
            segments.append((text[start:i], False))
        # Bloc à ignorer : tableau {| |}
        elif text[i:i+2] == '{|':
            start = i
            depth = 2
            i += 2
            while i < n and depth > 0:
                if text[i:i+2] == '{|':
                    depth +=2
                    i +=2
                elif text[i:i+2] == '|}':
                    depth -=2
                    i +=2
                else:
                    i +=1
            segments.append((text[start:i], False))
        # Bloc à ignorer : [ ] simples (pas [[ ]]
        elif text[i] == '[' and (i+1 >= n or text[i+1] != '['):
            start = i
            i +=1
            while i < n and text[i] != ']':
                i +=1
            i +=1
            segments.append((text[start:i], False))
        else:
            # segment à corriger
            start = i
            while i < n:
                if text[i:i+2] in ('{{','{|') or text[i:i+4] == '<!--':
                    break
                elif text[i] == '[' and (i+1 >= n or text[i+1] != '['):
                    break
                else:
                    i +=1
            segments.append((text[start:i], True))
    return segments

def fix_typos_segment(text):
    """
    Applique les corrections sur un segment à corriger
    """
    original = text

    # [[File: → [[Fichier:
    text = re.sub(r"\[\[\s*File\s*:", "[[Fichier:", text, flags=re.I)

    # Modèles avec guillemets typographiques «…» → {{"|…}}
    text = re.sub(r"«\s*(.*?)\s*»", r'{{"|\1}}', text)
    text = text.replace('«', '').replace('»', '')

    # Pas d'espaces avant le point
    text = re.sub(r'\s+\.', '.', text)

    # Ajouter un espace avant ! et ?
    text = re.sub(r'([^\s])([!?])', r'\1 \2', text)

    # Majuscule après point, ! ou ? suivi d'espace
    def capitalize(match):
        return match.group(1) + match.group(2).upper()
    text = re.sub(r'([.!?]\s+)([a-z])', capitalize, text)

    # Majuscule au début du texte
    if text:
        text = text[:1].upper() + text[1:]

    return text, text != original

def fix_typos_ignoring_blocks(text):
    segments = split_text_ignoring_blocks(text)
    new_text = ''
    changed = False
    for seg, to_fix in segments:
        if to_fix:
            fixed, ch = fix_typos_segment(seg)
            new_text += fixed
            changed = changed or ch
        else:
            new_text += seg
    return new_text, changed

pages_done = set()

for rc in site.recentchanges(
    namespaces=[0],
    changetype="edit",
    start=since,
    reverse=True
):
    title = rc["title"]
    if title in pages_done:
        continue
    pages_done.add(title)

    page = pywikibot.Page(site, title)

    try:
        text = page.get()
        new_text, changed = fix_typos_ignoring_blocks(text)

        if not changed:
            continue

        page.put(
            new_text,
            summary="Corrections typographiques",
            minor=True
        )
        print(f"✔ corrigé : {title}")
        time.sleep(1)

    except Exception as e:
        print(f"❌ erreur sur {title} : {e}")
        time.sleep(1)
