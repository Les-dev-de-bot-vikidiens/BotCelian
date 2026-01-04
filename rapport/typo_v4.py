#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de corrections typographiques V4 - SÉCURISÉ
Protection absolue des zones sensibles
"""

import re
import logging
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class SafeTypoFixer:
    """Correcteur typographique avec protection maximale"""
    
    # Abréviations protégées
    ABBREVS = ["J.-C.", "M.", "Mme.", "Mlle.", "Dr.", "etc.", "cf.", "p.", "vol.", "n°"]
    
    def __init__(self):
        self.protected_zones = {}
        self.protection_counter = 0
        self.changes_made = []
    
    def _protect_zone(self, match):
        """Protège une zone du traitement"""
        key = f"__PROTECT_{self.protection_counter}__"
        self.protection_counter += 1
        self.protected_zones[key] = match.group(0)
        return key
    
    def _restore_zones(self, text: str) -> str:
        """Restaure toutes les zones protégées"""
        for key, original in self.protected_zones.items():
            text = text.replace(key, original)
        return text
    
    def _protect_all_sensitive_zones(self, text: str) -> str:
        """
        Protège TOUTES les zones sensibles avant correction
        
        Zones protégées :
        - Liens internes [[...]]
        - Liens externes [http...]
        - Modèles {{...}}
        - Balises <ref>, <math>, <code>, <nowiki>, etc.
        - Galeries et tableaux
        """
        # 1. Protéger balises fermantes (importantes pour parsing)
        text = re.sub(r'</[^>]+>', self._protect_zone, text)
        
        # 2. Protéger balises auto-fermantes et ouvrantes avec contenu
        # <ref>, <math>, <code>, <nowiki>, <pre>, <source>, <syntaxhighlight>
        protected_tags = ['ref', 'math', 'code', 'nowiki', 'pre', 'source', 'syntaxhighlight', 'poem', 'score']
        for tag in protected_tags:
            # Balises avec contenu
            text = re.sub(
                rf'<{tag}[^>]*>.*?</{tag}>',
                self._protect_zone,
                text,
                flags=re.DOTALL | re.IGNORECASE
            )
            # Balises auto-fermantes
            text = re.sub(
                rf'<{tag}[^>]*/>', 
                self._protect_zone, 
                text,
                flags=re.IGNORECASE
            )
        
        # 3. Protéger modèles (imbriqués)
        # On protège de l'intérieur vers l'extérieur
        max_iterations = 10
        for _ in range(max_iterations):
            # Modèles sans imbrication
            before = text
            text = re.sub(
                r'\{\{(?:[^{}])*?\}\}',
                self._protect_zone,
                text
            )
            if text == before:
                break
        
        # 4. Protéger liens internes [[...]]
        # On protège aussi de l'intérieur vers l'extérieur
        for _ in range(max_iterations):
            before = text
            text = re.sub(
                r'\[\[(?:[^\[\]])*?\]\]',
                self._protect_zone,
                text
            )
            if text == before:
                break
        
        # 5. Protéger liens externes [http...]
        text = re.sub(
            r'\[(?:https?|ftp)://[^\]]+\]',
            self._protect_zone,
            text
        )
        
        # 6. Protéger URLs nues
        text = re.sub(
            r'(?:https?|ftp)://[^\s<>"{}|\\^\[\]`]+',
            self._protect_zone,
            text
        )
        
        # 7. Protéger galeries
        text = re.sub(
            r'<gallery[^>]*>.*?</gallery>',
            self._protect_zone,
            text,
            flags=re.DOTALL | re.IGNORECASE
        )
        
        # 8. Protéger tableaux wiki {| ... |}
        text = re.sub(
            r'\{\|.*?\|\}',
            self._protect_zone,
            text,
            flags=re.DOTALL
        )
        
        return text
    
    def _verify_no_protected_zones_modified(self, original: str, corrected: str) -> bool:
        """
        Vérifie qu'aucune zone protégée n'a été modifiée
        
        Returns:
            True si tout est OK, False si une zone protégée a changé
        """
        for key, original_content in self.protected_zones.items():
            if key in corrected:
                # La clé est toujours là, bon signe
                continue
            else:
                # La clé a disparu, GRAVE PROBLÈME
                logger.error(f"Zone protégée modifiée ou perdue: {original_content[:50]}")
                return False
        
        return True
    
    def fix(self, text: str) -> str:
        """
        Applique les corrections typographiques de manière SÉCURISÉE
        
        Args:
            text: Texte à corriger
            
        Returns:
            Texte corrigé OU texte original si problème détecté
        """
        if not text or not text.strip():
            return text
        
        # Réinitialiser
        self.protected_zones = {}
        self.protection_counter = 0
        self.changes_made = []
        
        original_text = text
        
        try:
            # ÉTAPE 1 : PROTECTION
            text = self._protect_all_sensitive_zones(text)
            
            # ÉTAPE 2 : CORRECTIONS (sur texte protégé)
            text = self._apply_corrections(text)
            
            # ÉTAPE 3 : RESTAURATION
            text = self._restore_zones(text)
            
            # ÉTAPE 4 : VÉRIFICATION FINALE
            if not self._verify_no_protected_zones_modified(original_text, text):
                logger.warning("⚠️ Zones protégées modifiées - ANNULATION des corrections")
                return original_text
            
            # ÉTAPE 5 : VÉRIFICATION LONGUEUR (détection corruption)
            original_len = len(original_text)
            corrected_len = len(text)
            
            # Si le texte a perdu plus de 5% ou gagné plus de 10%, suspect
            if corrected_len < original_len * 0.95 or corrected_len > original_len * 1.10:
                logger.warning(
                    f"⚠️ Changement de longueur suspect "
                    f"({original_len} → {corrected_len}) - ANNULATION"
                )
                return original_text
            
            return text
            
        except Exception as e:
            logger.error(f"Erreur dans corrections typo: {e}")
            # En cas d'erreur, TOUJOURS retourner l'original
            return original_text
    
    def _apply_corrections(self, text: str) -> str:
        """Applique les corrections sur le texte protégé"""
        
        # 1. Apostrophes typographiques
        text = re.sub(r"\s*'\s*", "'", text)
        text = re.sub(r"`", "'", text)
        
        # 2. Guillemets français
        # Ouvrant
        text = re.sub(r'«\s*', '« ', text)
        # Fermant
        text = re.sub(r'\s*»', ' »', text)
        # Pas plus de 2 espaces
        text = re.sub(r'«\s{2,}', '« ', text)
        text = re.sub(r'\s{2,}»', ' »', text)
        
        # 3. Parenthèses
        # Supprimer espaces internes
        text = re.sub(r'\(\s+', '(', text)
        text = re.sub(r'\s+\)', ')', text)
        # Ajouter espace avant (si manquant)
        text = re.sub(r'([^\s\(])\(', r'\1 (', text)
        # Ajouter espace après (si manquant)
        text = re.sub(r'\)([^\s\)\.,;:!?\-])', r') \1', text)
        
        # 4. Ponctuation basse : point et virgule
        # Supprimer espace avant
        text = re.sub(r'\s+([.,])', r'\1', text)
        # Ajouter espace après (sauf si chiffre suit pour nombres décimaux)
        text = re.sub(r'([.,])([^\s\d])', r'\1 \2', text)
        
        # 5. Ponctuation haute : ; : ! ?
        # Espace insécable avant (simulé par espace simple ici)
        # Espace normal après
        text = re.sub(r'\s*([;:!?])\s*', r' \1 ', text)
        
        # 6. Points de suspension
        text = re.sub(r'\.\s*\.\s*\.+', '...', text)
        text = re.sub(r'\.{4,}', '...', text)
        
        # 7. Tirets cadratins (pour incises)
        # Attention : ne pas toucher aux listes à puces
        text = re.sub(r'([^\n\-])\s+-\s+', r'\1 — ', text)
        
        # 8. Majuscules début de phrase
        def capitalize_sentence(match):
            prev, char = match.groups()
            # Ne pas capitaliser après abréviations
            for abbrev in self.ABBREVS:
                if prev.rstrip().endswith(abbrev):
                    return match.group(0)
            return prev + char.upper()
        
        text = re.sub(
            r'(^|[.!?]\s+)([a-zàâçéèêëîïôûùüÿñæœ])',
            capitalize_sentence,
            text,
            flags=re.MULTILINE
        )
        
        # 9. Espaces multiples
        text = re.sub(r'[ \t]{2,}', ' ', text)
        
        # 10. Espaces en fin de ligne
        text = re.sub(r'[ \t]+$', '', text, flags=re.MULTILINE)
        
        # 11. Lignes vides multiples (max 2)
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        return text
    
    def get_summary(self, before: str, after: str) -> str:
        """
        Génère un résumé intelligent des corrections
        
        Args:
            before: Texte avant
            after: Texte après
            
        Returns:
            Résumé des modifications
        """
        if before == after:
            return "Aucune correction typographique"
        
        changes = []
        
        # Détecter types de changements
        if '«' in before or '»' in before:
            changes.append("guillemets")
        
        if re.search(r'[!?;:]', before):
            changes.append("ponct. haute")
        
        if '(' in before and re.search(r'\(\s|\s\)', before):
            changes.append("parenthèses")
        
        if re.search(r'\.\s*\.\s*\.', before):
            changes.append("ellipses")
        
        if re.search(r"[''`]", before):
            changes.append("apostrophes")
        
        if re.search(r'\s+[.,;]', before):
            changes.append("espaces")
        
        if not changes:
            return "Corrections typographiques mineures"
        
        # Limiter à 3 pour résumé court
        changes = changes[:3]
        return f"Typo : {', '.join(changes)}"


# Fonction helper pour compatibilité
def fix_typo(text: str) -> str:
    """Helper pour corrections rapides"""
    fixer = SafeTypoFixer()
    return fixer.fix(text)


def typo_summary(before: str, after: str) -> str:
    """Helper pour résumé"""
    fixer = SafeTypoFixer()
    return fixer.get_summary(before, after)


# Alias pour compatibilité avec ancien code
class TypoFixer(SafeTypoFixer):
    """Alias pour compatibilité"""
    pass