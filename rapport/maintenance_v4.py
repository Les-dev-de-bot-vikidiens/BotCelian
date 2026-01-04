#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module maintenance V4 avec gestion ébauche intelligente par portails
"""

import re
import logging
from datetime import datetime, timezone
from typing import List, Tuple, Optional

logger = logging.getLogger(__name__)


class MaintenanceDetectorV4:
    """Détecteur avec gestion ébauche par portails"""
    
    def __init__(self, min_words_stub=50):
        self.min_words_stub = min_words_stub
    
    def has_template(self, text: str, template_name: str) -> bool:
        """Vérifie présence d'un modèle"""
        pattern = r"\{\{\s*" + re.escape(template_name) + r"\b"
        return bool(re.search(pattern, text, re.I))
    
    def is_in_progress(self, text: str) -> bool:
        """
        Vérifie si la page est en travaux
        
        Returns:
            True si en travaux (ne pas analyser)
        """
        work_templates = ["Travaux", "En travaux", "multi-travaux", "En cours"]
        
        for template in work_templates:
            if self.has_template(text, template):
                logger.info(f"Page en travaux détectée: {{{{{{template}}}}}}")
                return True
        
        return False
    
    def word_count(self, text: str) -> int:
        """Compte les mots (hors modèles et liens)"""
        # Retirer modèles
        text = re.sub(r'\{\{[^\}]*\}\}', '', text)
        # Retirer liens mais garder texte
        text = re.sub(r'\[\[[^\]|]*\|([^\]]*)\]\]', r'\1', text)
        text = re.sub(r'\[\[([^\]]*)\]\]', r'\1', text)
        return len(re.findall(r'\w+', text))
    
    def extract_existing_portals(self, text: str) -> List[str]:
        """
        Extrait les portails déjà présents dans le texte
        
        Returns:
            Liste des portails trouvés
        """
        portals = []
        
        # Chercher {{Portail|...}}
        portal_pattern = r'\{\{\s*Portail\s*\|([^}]+)\}\}'
        matches = re.finditer(portal_pattern, text, re.I)
        
        for match in matches:
            # Extraire les portails séparés par |
            content = match.group(1)
            portal_list = [p.strip() for p in content.split('|')]
            portals.extend(portal_list)
        
        logger.debug(f"Portails existants: {portals}")
        return portals
    
    def extract_existing_stub_portals(self, text: str) -> List[str]:
        """
        Extrait les portails du bandeau ébauche existant
        
        Returns:
            Liste des portails d'ébauche
        """
        portals = []
        
        # Chercher {{Ébauche|...}} ou {{ébauche|...}}
        stub_pattern = r'\{\{\s*[Éé]bauche\s*(?:\|([^}]+))?\}\}'
        matches = re.finditer(stub_pattern, text, re.I)
        
        for match in matches:
            if match.group(1):  # Y a des portails
                content = match.group(1)
                portal_list = [p.strip() for p in content.split('|')]
                portals.extend(portal_list)
        
        logger.debug(f"Portails ébauche existants: {portals}")
        return portals
    
    def detect_problems(self, text: str) -> List[str]:
        """Détecte les problèmes de maintenance"""
        problems = []
        
        # Catégorisation
        if not re.search(r"\[\[\s*Catégorie\s*:", text, re.I):
            auto_cat_templates = ["Infobox", "Palette", "Portail"]
            has_auto_cat = any(self.has_template(text, t) for t in auto_cat_templates)
            if not has_auto_cat:
                problems.append("catégoriser")
        
        # Portail
        if not re.search(r"\{\{\s*[Pp]ortail", text):
            problems.append("portail")
        
        # Illustration
        if not re.search(r"\[\[\s*(Fichier|Image)\s*:", text, re.I):
            if not re.search(r"\|\s*image\s*=", text, re.I):
                problems.append("illustrer")
        
        # Sources
        if not re.search(r"<ref|{{\s*Références", text, re.I):
            if self.word_count(text) > 100:
                problems.append("sourcer")
        
        # Wikification
        internal_links = re.findall(
            r"\[\[(?!Catégorie:|Fichier:|Image:|File:)[^\]|]+",
            text, re.I
        )
        if len(internal_links) < 3:
            problems.append("wikifier")
        
        return problems
    
    def needs_stub_template(
        self,
        text: str,
        ia_result: Optional[dict] = None
    ) -> Tuple[bool, List[str], str]:
        """
        Décision intelligente pour ébauche
        
        Args:
            text: Texte de l'article
            ia_result: Résultat analyse IA (avec needs_stub, portails)
            
        Returns:
            (needs_stub, portals, reason)
        """
        # Si déjà une ébauche, pas besoin d'en ajouter
        if self.has_template(text, "Ébauche") or self.has_template(text, "ébauche"):
            return False, [], "Ébauche déjà présente"
        
        word_count = self.word_count(text)
        
        # Critère 1 : Nombre de mots
        words_suggest_stub = word_count < self.min_words_stub
        
        # Critère 2 : Avis IA (si disponible)
        ia_suggests_stub = False
        ia_confidence = 0
        ia_portals = []
        
        if ia_result:
            ia_suggests_stub = ia_result.get("needs_stub", False)
            ia_confidence = ia_result.get("stub_confidence", 0)
            ia_portals = ia_result.get("portails", [])
        
        # DÉCISION COMBINÉE
        needs_stub = False
        reason = ""
        
        if words_suggest_stub and ia_suggests_stub:
            # Les deux sont d'accord
            needs_stub = True
            reason = f"Consensus mots ({word_count}) + IA ({ia_confidence}%)"
        elif words_suggest_stub and not ia_result:
            # Pas d'IA, critère mots seul
            needs_stub = True
            reason = f"Trop court ({word_count} mots)"
        elif words_suggest_stub and ia_confidence >= 70:
            # IA très confiante même si ne suggère pas
            needs_stub = ia_suggests_stub
            reason = f"IA confiante ({ia_confidence}%) sur ébauche={ia_suggests_stub}"
        elif not words_suggest_stub and ia_suggests_stub and ia_confidence >= 80:
            # IA très confiante que c'est une ébauche malgré nombre de mots OK
            needs_stub = True
            reason = f"IA très confiante ({ia_confidence}%) malgré {word_count} mots"
        else:
            # Pas d'ébauche
            needs_stub = False
            reason = f"Article suffisant ({word_count} mots)"
        
        # Déterminer portails
        portals = []
        if needs_stub:
            # Priorité aux portails IA
            if ia_portals:
                portals = ia_portals[:3]  # Max 3
            else:
                # Fallback : extraire des portails existants
                existing_portals = self.extract_existing_portals(text)
                if existing_portals:
                    portals = existing_portals[:3]
        
        logger.info(f"Décision ébauche: {needs_stub} - {reason}")
        if portals:
            logger.info(f"Portails ébauche: {portals}")
        
        return needs_stub, portals, reason
    
    def add_stub_template(self, text: str, portals: List[str] = None) -> str:
        """
        Ajoute bandeau ébauche avec portails
        
        Args:
            text: Texte original
            portals: Liste des portails (optionnel)
            
        Returns:
            Texte avec bandeau
        """
        if portals and len(portals) > 0:
            # Nettoyer portails (enlever espaces, capitaliser)
            clean_portals = [p.strip().capitalize() for p in portals if p.strip()]
            portals_str = "|".join(clean_portals)
            stub = f"{{{{Ébauche|{portals_str}}}}}"
        else:
            stub = "{{Ébauche}}"
        
        return stub + "\n" + text
    
    def needs_maintenance_template(self, text: str, problems: List[str]) -> bool:
        """Vérifie si maintenance nécessaire"""
        if not problems:
            return False
        if self.has_template(text, "Maintenance"):
            return False
        return True
    
    def add_maintenance_template(self, text: str, problems: List[str]) -> str:
        """Ajoute bandeau maintenance"""
        date = datetime.now(timezone.utc).strftime('%Y-%m-%d')
        jobs = ','.join(problems)
        template = f"{{{{Maintenance|job={jobs}|date={date}}}}}\n"
        return template + text
    
    def get_maintenance_summary(self, problems: List[str]) -> str:
        """Résumé maintenance"""
        return f"Ajout maintenance : {', '.join(problems)}"
    
    def get_stub_summary(self, portals: List[str] = None) -> str:
        """Résumé ébauche"""
        if portals:
            return f"Ajout ébauche ({', '.join(portals)})"
        return "Ajout ébauche"


# Helpers pour compatibilité
def detect_problems(text: str) -> List[str]:
    detector = MaintenanceDetectorV4()
    return detector.detect_problems(text)


def has_template(text: str, template_name: str) -> bool:
    detector = MaintenanceDetectorV4()
    return detector.has_template(text, template_name)


def word_count(text: str) -> int:
    detector = MaintenanceDetectorV4()
    return detector.word_count(text)


# Alias pour compatibilité
class MaintenanceDetector(MaintenanceDetectorV4):
    """Alias pour compatibilité"""
    pass