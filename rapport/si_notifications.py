#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de notifications dédiées pour les SI (Suppression Immédiate)
"""

import time
import logging
import urllib.parse
from typing import Dict, Optional, List
from datetime import datetime, timezone
from enum import Enum
import requests

logger = logging.getLogger(__name__)


class SIReason(Enum):
    """Raisons de SI"""
    VANDALISME = "vandalisme"
    LANGUE = "langue non francophone"
    AUTOPROMO = "autopromotion"
    CONTENU_SENSIBLE = "contenu sensible"
    COPIE = "copie détectée"
    SPAM = "spam"


class SIDecision:
    """Décision de SI avec justification"""
    
    def __init__(
        self,
        should_add_si: bool,
        reason: SIReason,
        confidence: int,
        details: str = "",
        severity: int = 3
    ):
        """
        Args:
            should_add_si: Si un SI doit être ajouté
            reason: Raison du SI
            confidence: Confiance (0-100)
            details: Détails additionnels
            severity: Gravité (1-5, 5 = plus grave)
        """
        self.should_add_si = should_add_si
        self.reason = reason
        self.confidence = confidence
        self.details = details
        self.severity = min(5, max(1, severity))
        self.timestamp = datetime.now(timezone.utc)
    
    def to_dict(self) -> Dict:
        """Convertit en dictionnaire"""
        return {
            "should_add_si": self.should_add_si,
            "reason": self.reason.value,
            "confidence": self.confidence,
            "details": self.details,
            "severity": self.severity,
            "timestamp": self.timestamp.isoformat()
        }


class SINotifier:
    """Gère les notifications SI"""
    
    def __init__(
        self,
        discord_webhook: Optional[str] = None,
        ntfy_topic: Optional[str] = None,
        enabled: bool = True,
        user_mentions: str = ""
    ):
        """
        Args:
            discord_webhook: URL webhook Discord
            ntfy_topic: Topic Ntfy
            enabled: Activer les notifications
            user_mentions: Mentions Discord (ex: "<@123> <@456>")
        """
        self.discord_webhook = discord_webhook
        self.ntfy_topic = ntfy_topic
        self.enabled = enabled
        self.user_mentions = user_mentions
        
        # Anti-spam : cooldown par page
        self.page_cooldowns = {}
        self.cooldown_duration = 300  # 5 minutes
        
        # Statistiques
        self.stats = {
            "notified": 0,
            "suppressed_cooldown": 0,
            "failed": 0
        }
    
    def _is_in_cooldown(self, page_title: str) -> bool:
        """
        Vérifie si une page est en cooldown
        
        Args:
            page_title: Titre de la page
            
        Returns:
            bool: True si en cooldown
        """
        if page_title not in self.page_cooldowns:
            return False
        
        last_notification = self.page_cooldowns[page_title]
        elapsed = time.time() - last_notification
        
        return elapsed < self.cooldown_duration
    
    def _set_cooldown(self, page_title: str):
        """
        Active le cooldown pour une page
        
        Args:
            page_title: Titre de la page
        """
        self.page_cooldowns[page_title] = time.time()
    
    def _format_diff_url(self, page_title: str, wiki_base: str = "https://fr.vikidia.org") -> str:
        """
        Génère l'URL du diff
        
        Args:
            page_title: Titre de la page
            wiki_base: URL de base du wiki
            
        Returns:
            URL du diff
        """
        encoded_title = urllib.parse.quote(page_title.replace(' ', '_'))
        return f"{wiki_base}/w/index.php?title={encoded_title}&diff=cur&oldid=prev"
    
    def _send_discord(
        self,
        page_title: str,
        decision: SIDecision,
        page_url: str,
        diff_url: str
    ) -> bool:
        """
        Envoie une notification Discord
        
        Args:
            page_title: Titre de la page
            decision: Décision SI
            page_url: URL de la page
            diff_url: URL du diff
            
        Returns:
            bool: True si succès
        """
        if not self.discord_webhook:
            return False
        
        # Couleur selon gravité
        colors = {
            1: 0xFFA500,  # Orange clair
            2: 0xFF8C00,  # Orange
            3: 0xFF4500,  # Rouge-orange
            4: 0xFF0000,  # Rouge
            5: 0x8B0000   # Rouge foncé
        }
        color = colors.get(decision.severity, 0xFF0000)
        
        # Emojis selon raison
        emoji_map = {
            SIReason.VANDALISME: "🚨",
            SIReason.LANGUE: "🌐",
            SIReason.AUTOPROMO: "📢",
            SIReason.CONTENU_SENSIBLE: "⚠️",
            SIReason.COPIE: "📋",
            SIReason.SPAM: "🗑️"
        }
        emoji = emoji_map.get(decision.reason, "⚠️")
        
        # Construction de l'embed
        embed = {
            "title": f"{emoji} SI détecté : {page_title}",
            "url": page_url,
            "color": color,
            "fields": [
                {
                    "name": "Raison",
                    "value": decision.reason.value,
                    "inline": True
                },
                {
                    "name": "Confiance",
                    "value": f"{decision.confidence}%",
                    "inline": True
                },
                {
                    "name": "Gravité",
                    "value": "⭐" * decision.severity,
                    "inline": True
                },
                {
                    "name": "Détails",
                    "value": decision.details or "Aucun détail supplémentaire",
                    "inline": False
                },
                {
                    "name": "Actions",
                    "value": f"[Voir la page]({page_url}) • [Voir le diff]({diff_url})",
                    "inline": False
                }
            ],
            "footer": {
                "text": "BotCélian - Détection SI"
            },
            "timestamp": decision.timestamp.isoformat()
        }
        
        payload = {
            "content": self.user_mentions,
            "embeds": [embed]
        }
        
        try:
            response = requests.post(
                self.discord_webhook,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Notification Discord SI envoyée: {page_title}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur notification Discord SI: {e}")
            return False
    
    def _send_ntfy(
        self,
        page_title: str,
        decision: SIDecision,
        page_url: str
    ) -> bool:
        """
        Envoie une notification Ntfy
        
        Args:
            page_title: Titre de la page
            decision: Décision SI
            page_url: URL de la page
            
        Returns:
            bool: True si succès
        """
        if not self.ntfy_topic:
            return False
        
        url = f"https://ntfy.sh/{self.ntfy_topic}"
        
        # Priorité selon gravité
        priority = min(5, max(1, decision.severity))
        
        message = (
            f"SI détecté: {page_title}\n"
            f"Raison: {decision.reason.value}\n"
            f"Confiance: {decision.confidence}%\n"
            f"Détails: {decision.details}\n"
            f"Lien: {page_url}"
        )
        
        try:
            response = requests.post(
                url,
                data=message.encode('utf-8'),
                headers={
                    "Title": f"SI - {page_title}",
                    "Priority": str(priority),
                    "Tags": "warning,rotating_light",
                    "Click": page_url
                },
                timeout=10
            )
            response.raise_for_status()
            logger.info(f"Notification Ntfy SI envoyée: {page_title}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur notification Ntfy SI: {e}")
            return False
    
    def notify(
        self,
        page_title: str,
        decision: SIDecision,
        wiki_base: str = "https://fr.vikidia.org"
    ) -> bool:
        """
        Envoie une notification SI
        
        Args:
            page_title: Titre de la page
            decision: Décision SI
            wiki_base: URL de base du wiki
            
        Returns:
            bool: True si au moins une notification réussie
        """
        if not self.enabled:
            logger.debug("Notifications SI désactivées")
            return False
        
        if not decision.should_add_si:
            logger.debug(f"Pas de SI pour {page_title}")
            return False
        
        # Vérifier cooldown
        if self._is_in_cooldown(page_title):
            logger.info(f"Page en cooldown: {page_title}")
            self.stats["suppressed_cooldown"] += 1
            return False
        
        # URLs
        encoded_title = urllib.parse.quote(page_title.replace(' ', '_'))
        page_url = f"{wiki_base}/wiki/{encoded_title}"
        diff_url = self._format_diff_url(page_title, wiki_base)
        
        # Envoyer sur tous les canaux
        success = False
        
        if self._send_discord(page_title, decision, page_url, diff_url):
            success = True
        
        if self._send_ntfy(page_title, decision, page_url):
            success = True
        
        # Activer cooldown
        if success:
            self._set_cooldown(page_title)
            self.stats["notified"] += 1
        else:
            self.stats["failed"] += 1
        
        return success
    
    def notify_batch(
        self,
        notifications: List[tuple],
        wiki_base: str = "https://fr.vikidia.org"
    ) -> int:
        """
        Envoie plusieurs notifications en batch
        
        Args:
            notifications: Liste de (page_title, decision)
            wiki_base: URL de base du wiki
            
        Returns:
            Nombre de notifications réussies
        """
        success_count = 0
        
        for page_title, decision in notifications:
            if self.notify(page_title, decision, wiki_base):
                success_count += 1
        
        return success_count
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques"""
        return self.stats.copy()


class SIDetector:
    """Détecte si un SI doit être ajouté"""
    
    @staticmethod
    def from_ia_result(result: Dict) -> Optional[SIDecision]:
        """
        Crée une décision SI depuis un résultat IA
        
        Args:
            result: Résultat de l'analyse IA
            
        Returns:
            SIDecision ou None
        """
        confidence = result.get("confiance", 0)
        
        # Vandalisme
        if result.get("vandalisme", False):
            return SIDecision(
                should_add_si=True,
                reason=SIReason.VANDALISME,
                confidence=confidence,
                details=result.get("justification", ""),
                severity=5
            )
        
        # Langue
        if not result.get("langue_fr", True):
            return SIDecision(
                should_add_si=True,
                reason=SIReason.LANGUE,
                confidence=confidence,
                details=result.get("justification", ""),
                severity=3
            )
        
        # Autopromo
        if result.get("autopromo", False):
            # Seuil de confiance pour autopromo
            if confidence >= 70:
                return SIDecision(
                    should_add_si=True,
                    reason=SIReason.AUTOPROMO,
                    confidence=confidence,
                    details=result.get("justification", ""),
                    severity=4
                )
        
        return None


# Singleton global
_notifier_instance = None


def get_notifier(
    discord_webhook: Optional[str] = None,
    ntfy_topic: Optional[str] = None,
    enabled: bool = True,
    user_mentions: str = ""
) -> SINotifier:
    """
    Récupère l'instance singleton du notifier SI
    
    Args:
        discord_webhook: Webhook Discord
        ntfy_topic: Topic Ntfy
        enabled: Activer
        user_mentions: Mentions
        
    Returns:
        Instance de SINotifier
    """
    global _notifier_instance
    if _notifier_instance is None:
        _notifier_instance = SINotifier(
            discord_webhook=discord_webhook,
            ntfy_topic=ntfy_topic,
            enabled=enabled,
            user_mentions=user_mentions
        )
    return _notifier_instance