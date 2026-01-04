#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module Averto - Détection de copie et autopromotion
"""

import re
import logging
from typing import Dict, List, Optional, Tuple
from difflib import SequenceMatcher
import requests
from urllib.parse import quote

logger = logging.getLogger(__name__)


class CopySource:
    """Source de copie détectée"""
    
    def __init__(
        self,
        source_name: str,
        url: str,
        similarity: float,
        matched_text: str = ""
    ):
        """
        Args:
            source_name: Nom de la source (Wikipedia, Wikimini, etc.)
            url: URL de la source
            similarity: Score de similarité (0-1)
            matched_text: Texte correspondant
        """
        self.source_name = source_name
        self.url = url
        self.similarity = similarity
        self.matched_text = matched_text
    
    def to_dict(self) -> Dict:
        return {
            "source": self.source_name,
            "url": self.url,
            "similarity": round(self.similarity, 3),
            "matched_text": self.matched_text[:200]  # Limiter la taille
        }


class AvertoDecision:
    """Décision du module Averto"""
    
    def __init__(
        self,
        action: str,  # "si", "warning", "log"
        reason: str,
        confidence: float,
        sources: List[CopySource] = None,
        details: str = ""
    ):
        """
        Args:
            action: Action recommandée (si/warning/log)
            reason: Raison de la décision
            confidence: Confiance (0-1)
            sources: Sources détectées
            details: Détails additionnels
        """
        self.action = action
        self.reason = reason
        self.confidence = confidence
        self.sources = sources or []
        self.details = details
    
    def to_dict(self) -> Dict:
        return {
            "action": self.action,
            "reason": self.reason,
            "confidence": round(self.confidence, 3),
            "sources": [s.to_dict() for s in self.sources],
            "details": self.details
        }


class AvertoDetector:
    """Détecteur de copie et autopromotion"""
    
    def __init__(
        self,
        similarity_threshold: float = 0.7,
        min_text_length: int = 100,
        check_wikipedia: bool = True,
        check_wikimini: bool = True,
        user_agent: str = "BotCelian/1.0"
    ):
        """
        Args:
            similarity_threshold: Seuil de similarité pour copie
            min_text_length: Longueur minimale pour vérifier
            check_wikipedia: Vérifier Wikipedia
            check_wikimini: Vérifier Wikimini
            user_agent: User agent pour requêtes HTTP
        """
        self.similarity_threshold = similarity_threshold
        self.min_text_length = min_text_length
        self.check_wikipedia = check_wikipedia
        self.check_wikimini = check_wikimini
        self.user_agent = user_agent
        
        # Statistiques
        self.stats = {
            "checked": 0,
            "copies_detected": 0,
            "autopromo_detected": 0,
            "api_errors": 0
        }
    
    def _clean_text(self, text: str) -> str:
        """
        Nettoie le texte pour comparaison
        
        Args:
            text: Texte à nettoyer
            
        Returns:
            Texte nettoyé
        """
        # Retirer les modèles wiki
        text = re.sub(r'\{\{[^\}]*\}\}', '', text)
        # Retirer les liens
        text = re.sub(r'\[\[[^\]]*\]\]', '', text)
        # Retirer balises HTML
        text = re.sub(r'<[^>]+>', '', text)
        # Normaliser espaces
        text = re.sub(r'\s+', ' ', text)
        return text.strip().lower()
    
    def _calculate_similarity(self, text1: str, text2: str) -> float:
        """
        Calcule la similarité entre deux textes
        
        Args:
            text1: Premier texte
            text2: Deuxième texte
            
        Returns:
            Score de similarité (0-1)
        """
        clean1 = self._clean_text(text1)
        clean2 = self._clean_text(text2)
        
        if not clean1 or not clean2:
            return 0.0
        
        return SequenceMatcher(None, clean1, clean2).ratio()
    
    def _check_wikipedia(self, title: str, text: str) -> Optional[CopySource]:
        """
        Vérifie si le contenu existe sur Wikipedia
        
        Args:
            title: Titre de l'article
            text: Contenu à vérifier
            
        Returns:
            CopySource si copie détectée, None sinon
        """
        if not self.check_wikipedia:
            return None
        
        url = "https://fr.wikipedia.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "extracts",
            "explaintext": True,
            "exintro": True
        }
        
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return None
            
            page = next(iter(pages.values()))
            if "extract" not in page:
                return None
            
            wp_text = page["extract"]
            similarity = self._calculate_similarity(text, wp_text)
            
            if similarity >= self.similarity_threshold:
                page_url = f"https://fr.wikipedia.org/wiki/{quote(title)}"
                logger.info(f"Copie Wikipedia détectée: {title} (sim: {similarity:.2f})")
                return CopySource(
                    source_name="Wikipedia",
                    url=page_url,
                    similarity=similarity,
                    matched_text=wp_text[:300]
                )
            
        except Exception as e:
            logger.error(f"Erreur vérification Wikipedia: {e}")
            self.stats["api_errors"] += 1
        
        return None
    
    def _check_wikimini(self, title: str, text: str) -> Optional[CopySource]:
        """
        Vérifie si le contenu existe sur Wikimini
        
        Args:
            title: Titre de l'article
            text: Contenu à vérifier
            
        Returns:
            CopySource si copie détectée, None sinon
        """
        if not self.check_wikimini:
            return None
        
        url = "https://fr.wikimini.org/w/api.php"
        params = {
            "action": "query",
            "format": "json",
            "titles": title,
            "prop": "extracts",
            "explaintext": True
        }
        
        try:
            response = requests.get(
                url,
                params=params,
                headers={"User-Agent": self.user_agent},
                timeout=10
            )
            response.raise_for_status()
            data = response.json()
            
            pages = data.get("query", {}).get("pages", {})
            if not pages:
                return None
            
            page = next(iter(pages.values()))
            if "extract" not in page:
                return None
            
            wm_text = page["extract"]
            similarity = self._calculate_similarity(text, wm_text)
            
            if similarity >= self.similarity_threshold:
                page_url = f"https://fr.wikimini.org/wiki/{quote(title)}"
                logger.info(f"Copie Wikimini détectée: {title} (sim: {similarity:.2f})")
                return CopySource(
                    source_name="Wikimini",
                    url=page_url,
                    similarity=similarity,
                    matched_text=wm_text[:300]
                )
            
        except Exception as e:
            logger.error(f"Erreur vérification Wikimini: {e}")
            self.stats["api_errors"] += 1
        
        return None
    
    def _detect_autopromo(self, text: str, creator: str = "") -> Tuple[bool, float, str]:
        """
        Détecte l'autopromotion
        
        Args:
            text: Texte à analyser
            creator: Nom du créateur (optionnel)
            
        Returns:
            (is_autopromo, confidence, details)
        """
        indicators = []
        score = 0.0
        
        # Patterns suspects
        promo_patterns = [
            (r'\b(acheter|achat|commander|prix|promotion|offre|gratuit)\b', 0.3),
            (r'\b(meilleur|excellent|parfait|idéal|unique)\b', 0.2),
            (r'\b(www\.|http|\.com|\.fr)\b', 0.4),
            (r'\b(contact|téléphone|email|@)\b', 0.3),
            (r'\b(notre|nos) (produit|service|entreprise|société)\b', 0.4)
        ]
        
        text_lower = text.lower()
        
        for pattern, weight in promo_patterns:
            if re.search(pattern, text_lower):
                indicators.append(pattern)
                score += weight
        
        # Vérifier si le titre contient le nom du créateur
        if creator and len(creator) > 3:
            if creator.lower() in text_lower[:200]:  # Dans les 200 premiers caractères
                indicators.append("nom créateur dans texte")
                score += 0.3
        
        # URLs externes nombreuses
        external_urls = len(re.findall(r'https?://', text))
        if external_urls > 2:
            indicators.append(f"{external_urls} URLs externes")
            score += 0.2
        
        confidence = min(1.0, score)
        is_autopromo = confidence >= 0.5
        
        details = ", ".join(indicators) if indicators else "Aucun indicateur"
        
        return is_autopromo, confidence, details
    
    def detect(
        self,
        title: str,
        text: str,
        creator: str = ""
    ) -> AvertoDecision:
        """
        Détecte copie et autopromotion
        
        Args:
            title: Titre de la page
            text: Contenu de la page
            creator: Créateur de la page (optionnel)
            
        Returns:
            AvertoDecision
        """
        self.stats["checked"] += 1
        
        # Vérifier longueur minimale
        if len(text) < self.min_text_length:
            return AvertoDecision(
                action="log",
                reason="Texte trop court pour analyse",
                confidence=0.0,
                details=f"Longueur: {len(text)} caractères"
            )
        
        sources = []
        
        # Vérifier Wikipedia
        wp_source = self._check_wikipedia(title, text)
        if wp_source:
            sources.append(wp_source)
            self.stats["copies_detected"] += 1
        
        # Vérifier Wikimini
        wm_source = self._check_wikimini(title, text)
        if wm_source:
            sources.append(wm_source)
            self.stats["copies_detected"] += 1
        
        # Si copie détectée avec haute similarité
        if sources:
            max_similarity = max(s.similarity for s in sources)
            
            if max_similarity >= 0.9:
                # Copie quasi-identique -> SI
                return AvertoDecision(
                    action="si",
                    reason="Copie quasi-identique détectée",
                    confidence=max_similarity,
                    sources=sources,
                    details=f"Similarité maximale: {max_similarity:.2%}"
                )
            elif max_similarity >= self.similarity_threshold:
                # Copie probable -> Warning
                return AvertoDecision(
                    action="warning",
                    reason="Copie probable détectée",
                    confidence=max_similarity,
                    sources=sources,
                    details=f"Similarité: {max_similarity:.2%}"
                )
        
        # Vérifier autopromotion
        is_autopromo, promo_confidence, promo_details = self._detect_autopromo(text, creator)
        
        if is_autopromo:
            self.stats["autopromo_detected"] += 1
            
            if promo_confidence >= 0.8:
                # Autopromo claire -> SI
                return AvertoDecision(
                    action="si",
                    reason="Autopromotion détectée",
                    confidence=promo_confidence,
                    details=promo_details
                )
            else:
                # Autopromo possible -> Warning
                return AvertoDecision(
                    action="warning",
                    reason="Autopromotion possible",
                    confidence=promo_confidence,
                    details=promo_details
                )
        
        # Rien de suspect
        return AvertoDecision(
            action="log",
            reason="Aucun problème détecté",
            confidence=1.0,
            details="Contenu semble original"
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques"""
        return self.stats.copy()


# Fonction helper
def detect_copy_and_promo(title: str, text: str, creator: str = "") -> AvertoDecision:
    """
    Helper pour détection rapide
    
    Args:
        title: Titre
        text: Texte
        creator: Créateur
        
    Returns:
        AvertoDecision
    """
    detector = AvertoDetector()
    return detector.detect(title, text, creator)