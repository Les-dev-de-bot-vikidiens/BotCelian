#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de détection de termes sensibles pour SI immédiate
"""

import re
import json
import logging
from typing import Dict, List, Set, Optional, Tuple
from pathlib import Path
from unicodedata import normalize

logger = logging.getLogger(__name__)


class SensitiveCategory:
    """Catégorie de termes sensibles"""
    
    INSULTES = "insultes"
    PORNOGRAPHIE = "pornographie"
    VIOLENCE = "violence"
    HAINE = "haine"
    DROGUES = "drogues"
    SPAM = "spam"


class SensitiveMatch:
    """Match de terme sensible trouvé"""
    
    def __init__(
        self,
        term: str,
        category: str,
        severity: int,
        context: str = ""
    ):
        """
        Args:
            term: Terme trouvé
            category: Catégorie
            severity: Gravité (1-5)
            context: Contexte du match
        """
        self.term = term
        self.category = category
        self.severity = severity
        self.context = context
    
    def to_dict(self) -> Dict:
        return {
            "term": self.term,
            "category": self.category,
            "severity": self.severity,
            "context": self.context
        }


class SensitiveTermsDetector:
    """Détecteur de termes sensibles"""
    
    def __init__(self, config_file: str = "sensitive_terms.json"):
        """
        Args:
            config_file: Fichier de configuration JSON
        """
        self.config_file = Path(config_file)
        self.terms: Dict[str, List[Dict]] = {}
        self.exclusions: Set[str] = set()
        self.excluded_categories: Set[str] = set()
        
        # Charger la configuration
        self._load_config()
        
        # Statistiques
        self.stats = {
            "checks": 0,
            "matches": 0,
            "false_positives_avoided": 0
        }
    
    def _load_config(self):
        """Charge la configuration depuis le fichier JSON"""
        if not self.config_file.exists():
            logger.warning(f"Fichier de config introuvable: {self.config_file}")
            self._create_default_config()
            return
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            self.terms = config.get("terms", {})
            self.exclusions = set(config.get("exclusions", []))
            self.excluded_categories = set(config.get("excluded_categories", []))
            
            logger.info(f"Config chargée: {sum(len(t) for t in self.terms.values())} termes")
            
        except Exception as e:
            logger.error(f"Erreur chargement config: {e}")
            self._create_default_config()
    
    def _create_default_config(self):
        """Crée une configuration par défaut"""
        default_config = {
            "terms": {
                SensitiveCategory.INSULTES: [
                    {"pattern": r"\bcon\b", "severity": 2},
                    {"pattern": r"\bconnard\b", "severity": 3},
                    {"pattern": r"\bputain\b", "severity": 2},
                    {"pattern": r"\bmerde\b", "severity": 2}
                ],
                SensitiveCategory.PORNOGRAPHIE: [
                    {"pattern": r"\bporn[oe]\b", "severity": 5},
                    {"pattern": r"\bsex[e]?\b(?!tuplé|tuor)", "severity": 4},
                    {"pattern": r"\bnud[e]?s?\b", "severity": 3}
                ],
                SensitiveCategory.VIOLENCE: [
                    {"pattern": r"\btuer\b", "severity": 4},
                    {"pattern": r"\bmassacre\b", "severity": 5},
                    {"pattern": r"\bvioler\b", "severity": 5}
                ],
                SensitiveCategory.HAINE: [
                    {"pattern": r"\braciste\b", "severity": 4},
                    {"pattern": r"\bnazi\b", "severity": 4},
                    {"pattern": r"\bfasciste\b", "severity": 3}
                ],
                SensitiveCategory.DROGUES: [
                    {"pattern": r"\bcocaïne\b", "severity": 3},
                    {"pattern": r"\bhéroïne\b", "severity": 3},
                    {"pattern": r"\bdrogue\b", "severity": 2}
                ]
            },
            "exclusions": [
                "Utilisateur:",
                "Discussion:",
                "Liste des",
                "Catégorie:"
            ],
            "excluded_categories": []
        }
        
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, ensure_ascii=False, indent=2)
            logger.info(f"Config par défaut créée: {self.config_file}")
            self.terms = default_config["terms"]
            self.exclusions = set(default_config["exclusions"])
        except Exception as e:
            logger.error(f"Erreur création config par défaut: {e}")
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalise le texte pour détection robuste
        
        Args:
            text: Texte à normaliser
            
        Returns:
            Texte normalisé
        """
        # Normalisation Unicode (supprimer accents variables)
        text = normalize('NFKD', text)
        
        # Minuscules
        text = text.lower()
        
        # Remplacer variations courantes
        replacements = {
            '0': 'o',
            '1': 'i',
            '3': 'e',
            '4': 'a',
            '5': 's',
            '7': 't',
            '@': 'a',
            '$': 's',
            '€': 'e'
        }
        
        for old, new in replacements.items():
            text = text.replace(old, new)
        
        # Supprimer caractères spéciaux ajoutés pour contourner filtres
        text = re.sub(r'[_\-\*\+\.]{2,}', '', text)
        
        return text
    
    def _extract_context(self, text: str, match_pos: int, context_len: int = 50) -> str:
        """
        Extrait le contexte autour d'un match
        
        Args:
            text: Texte complet
            match_pos: Position du match
            context_len: Longueur du contexte de chaque côté
            
        Returns:
            Contexte
        """
        start = max(0, match_pos - context_len)
        end = min(len(text), match_pos + context_len)
        
        context = text[start:end]
        
        if start > 0:
            context = "..." + context
        if end < len(text):
            context = context + "..."
        
        return context.strip()
    
    def _should_exclude(self, title: str, categories: List[str]) -> bool:
        """
        Vérifie si la page doit être exclue
        
        Args:
            title: Titre de la page
            categories: Catégories de la page
            
        Returns:
            bool: True si exclue
        """
        # Vérifier titre
        for exclusion in self.exclusions:
            if exclusion.lower() in title.lower():
                self.stats["false_positives_avoided"] += 1
                return True
        
        # Vérifier catégories
        for category in categories:
            if category in self.excluded_categories:
                self.stats["false_positives_avoided"] += 1
                return True
        
        return False
    
    def detect(
        self,
        text: str,
        title: str = "",
        categories: List[str] = None
    ) -> Tuple[List[SensitiveMatch], int]:
        """
        Détecte les termes sensibles
        
        Args:
            text: Texte à analyser
            title: Titre de la page (pour exclusions)
            categories: Catégories de la page (pour exclusions)
            
        Returns:
            (matches, max_severity)
        """
        self.stats["checks"] += 1
        
        if not text or not text.strip():
            return [], 0
        
        # Vérifier exclusions
        if self._should_exclude(title, categories or []):
            return [], 0
        
        # Normaliser le texte
        normalized = self._normalize_text(text)
        
        matches = []
        max_severity = 0
        
        # Parcourir toutes les catégories
        for category, term_list in self.terms.items():
            for term_data in term_list:
                pattern = term_data.get("pattern", "")
                severity = term_data.get("severity", 1)
                
                # Chercher les matches
                for match in re.finditer(pattern, normalized, re.IGNORECASE):
                    self.stats["matches"] += 1
                    
                    # Extraire contexte
                    context = self._extract_context(text, match.start())
                    
                    matches.append(SensitiveMatch(
                        term=match.group(0),
                        category=category,
                        severity=severity,
                        context=context
                    ))
                    
                    max_severity = max(max_severity, severity)
        
        return matches, max_severity
    
    def should_add_si(
        self,
        text: str,
        title: str = "",
        categories: List[str] = None,
        severity_threshold: int = 4
    ) -> Tuple[bool, List[SensitiveMatch], str]:
        """
        Détermine si un SI doit être ajouté
        
        Args:
            text: Texte à analyser
            title: Titre de la page
            categories: Catégories
            severity_threshold: Seuil de gravité pour SI
            
        Returns:
            (should_add_si, matches, reason)
        """
        matches, max_severity = self.detect(text, title, categories)
        
        if not matches:
            return False, [], ""
        
        # SI si gravité élevée
        if max_severity >= severity_threshold:
            reason = f"Contenu sensible détecté ({matches[0].category})"
            return True, matches, reason
        
        # Sinon juste signaler
        return False, matches, f"Termes sensibles de faible gravité ({len(matches)} trouvés)"
    
    def get_report(self, matches: List[SensitiveMatch]) -> str:
        """
        Génère un rapport lisible des matches
        
        Args:
            matches: Liste des matches
            
        Returns:
            Rapport formaté
        """
        if not matches:
            return "Aucun terme sensible détecté"
        
        report_lines = [f"⚠️ {len(matches)} terme(s) sensible(s) détecté(s):"]
        
        # Grouper par catégorie
        by_category = {}
        for match in matches:
            if match.category not in by_category:
                by_category[match.category] = []
            by_category[match.category].append(match)
        
        for category, cat_matches in by_category.items():
            report_lines.append(f"\n📌 {category.upper()} ({len(cat_matches)}):")
            for match in cat_matches[:3]:  # Limiter à 3 par catégorie
                report_lines.append(f"  - '{match.term}' (gravité {match.severity})")
                report_lines.append(f"    Contexte: {match.context}")
        
        return "\n".join(report_lines)
    
    def add_term(
        self,
        category: str,
        pattern: str,
        severity: int
    ):
        """
        Ajoute un nouveau terme à la configuration
        
        Args:
            category: Catégorie
            pattern: Pattern regex
            severity: Gravité (1-5)
        """
        if category not in self.terms:
            self.terms[category] = []
        
        self.terms[category].append({
            "pattern": pattern,
            "severity": min(5, max(1, severity))
        })
        
        # Sauvegarder
        self._save_config()
    
    def _save_config(self):
        """Sauvegarde la configuration"""
        try:
            config = {
                "terms": self.terms,
                "exclusions": list(self.exclusions),
                "excluded_categories": list(self.excluded_categories)
            }
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            
            logger.info("Configuration sauvegardée")
        except Exception as e:
            logger.error(f"Erreur sauvegarde config: {e}")
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques"""
        return self.stats.copy()


# Singleton global
_detector_instance = None


def get_detector(config_file: str = "sensitive_terms.json") -> SensitiveTermsDetector:
    """
    Récupère l'instance singleton du détecteur
    
    Args:
        config_file: Fichier de configuration
        
    Returns:
        Instance de SensitiveTermsDetector
    """
    global _detector_instance
    if _detector_instance is None:
        _detector_instance = SensitiveTermsDetector(config_file)
    return _detector_instance


# Fonction helper
def detect_sensitive_terms(text: str, title: str = "") -> Tuple[List[SensitiveMatch], int]:
    """
    Helper pour détection rapide
    
    Args:
        text: Texte à analyser
        title: Titre
        
    Returns:
        (matches, max_severity)
    """
    detector = get_detector()
    return detector.detect(text, title)