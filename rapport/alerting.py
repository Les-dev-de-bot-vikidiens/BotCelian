#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Système d'alertes critiques pour monitoring du bot
"""

import logging
import time
import traceback
from typing import Dict, Any, Optional
from datetime import datetime, timezone
from enum import Enum
import requests

logger = logging.getLogger(__name__)


class AlertLevel(Enum):
    """Niveaux d'alerte"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertingSystem:
    """Système d'alertes multi-canaux"""
    
    def __init__(
        self,
        ntfy_topic: Optional[str] = None,
        ntfy_server: str = "https://ntfy.sh",
        pushover_token: Optional[str] = None,
        pushover_user: Optional[str] = None,
        fallback_file: str = "logs/alerts.log",
        enabled: bool = True
    ):
        """
        Args:
            ntfy_topic: Topic Ntfy (ex: "botcelian-alerts")
            ntfy_server: Serveur Ntfy
            pushover_token: Token API Pushover
            pushover_user: User key Pushover
            fallback_file: Fichier de logs fallback
            enabled: Activer/désactiver les alertes
        """
        self.ntfy_topic = ntfy_topic
        self.ntfy_server = ntfy_server
        self.pushover_token = pushover_token
        self.pushover_user = pushover_user
        self.fallback_file = fallback_file
        self.enabled = enabled
        
        # Anti-spam
        self.last_alert_time = {}
        self.min_alert_interval = 60  # 1 minute entre alertes similaires
        
        # Statistiques
        self.stats = {
            "sent": 0,
            "failed": 0,
            "suppressed": 0
        }
    
    def _should_send_alert(self, message: str) -> bool:
        """
        Vérifie si l'alerte doit être envoyée (anti-spam)
        
        Args:
            message: Message de l'alerte
            
        Returns:
            bool: True si l'alerte doit être envoyée
        """
        if not self.enabled:
            return False
        
        # Hash simple du message pour détecter duplicatas
        msg_hash = hash(message)
        current_time = time.time()
        
        if msg_hash in self.last_alert_time:
            time_since_last = current_time - self.last_alert_time[msg_hash]
            if time_since_last < self.min_alert_interval:
                self.stats["suppressed"] += 1
                logger.debug(f"Alerte supprimée (spam): {message[:50]}")
                return False
        
        self.last_alert_time[msg_hash] = current_time
        return True
    
    def _get_priority(self, level: AlertLevel) -> int:
        """
        Convertit le niveau d'alerte en priorité Ntfy/Pushover
        
        Args:
            level: Niveau d'alerte
            
        Returns:
            int: Priorité (1-5)
        """
        priority_map = {
            AlertLevel.INFO: 1,
            AlertLevel.WARNING: 3,
            AlertLevel.ERROR: 4,
            AlertLevel.CRITICAL: 5
        }
        return priority_map.get(level, 3)
    
    def _send_ntfy(self, level: AlertLevel, message: str, title: str) -> bool:
        """
        Envoie une alerte via Ntfy
        
        Args:
            level: Niveau d'alerte
            message: Message
            title: Titre
            
        Returns:
            bool: True si succès
        """
        if not self.ntfy_topic:
            return False
        
        url = f"{self.ntfy_server}/{self.ntfy_topic}"
        priority = self._get_priority(level)
        
        # Tags selon niveau
        tags_map = {
            AlertLevel.INFO: "robot",
            AlertLevel.WARNING: "warning",
            AlertLevel.ERROR: "x",
            AlertLevel.CRITICAL: "rotating_light"
        }
        tag = tags_map.get(level, "robot")
        
        try:
            response = requests.post(
                url,
                data=message.encode('utf-8'),
                headers={
                    "Title": title,
                    "Priority": str(priority),
                    "Tags": tag
                },
                timeout=10
            )
            response.raise_for_status()
            logger.debug(f"Alerte Ntfy envoyée: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi Ntfy: {e}")
            return False
    
    def _send_pushover(self, level: AlertLevel, message: str, title: str) -> bool:
        """
        Envoie une alerte via Pushover
        
        Args:
            level: Niveau d'alerte
            message: Message
            title: Titre
            
        Returns:
            bool: True si succès
        """
        if not (self.pushover_token and self.pushover_user):
            return False
        
        url = "https://api.pushover.net/1/messages.json"
        priority = self._get_priority(level) - 3  # Pushover: -2 à 2
        
        data = {
            "token": self.pushover_token,
            "user": self.pushover_user,
            "title": title,
            "message": message,
            "priority": priority
        }
        
        try:
            response = requests.post(url, data=data, timeout=10)
            response.raise_for_status()
            logger.debug(f"Alerte Pushover envoyée: {title}")
            return True
            
        except Exception as e:
            logger.error(f"Erreur envoi Pushover: {e}")
            return False
    
    def _write_fallback(self, level: AlertLevel, message: str, context: Dict[str, Any]):
        """
        Écrit l'alerte dans le fichier fallback
        
        Args:
            level: Niveau d'alerte
            message: Message
            context: Contexte
        """
        try:
            timestamp = datetime.now(timezone.utc).isoformat()
            log_entry = f"[{timestamp}] [{level.value.upper()}] {message}\n"
            
            if context:
                log_entry += f"Context: {context}\n"
            
            log_entry += "-" * 80 + "\n"
            
            with open(self.fallback_file, 'a', encoding='utf-8') as f:
                f.write(log_entry)
            
        except Exception as e:
            logger.error(f"Erreur écriture fallback: {e}")
    
    def alert(
        self,
        level: AlertLevel,
        message: str,
        context: Optional[Dict[str, Any]] = None,
        title: Optional[str] = None
    ):
        """
        Envoie une alerte multi-canaux
        
        Args:
            level: Niveau d'alerte
            message: Message de l'alerte
            context: Contexte additionnel (optionnel)
            title: Titre personnalisé (optionnel)
        """
        if not self._should_send_alert(message):
            return
        
        # Titre par défaut
        if title is None:
            title = f"BotCélian - {level.value.upper()}"
        
        # Ajouter contexte au message si présent
        full_message = message
        if context:
            context_str = "\n".join(f"{k}: {v}" for k, v in context.items())
            full_message = f"{message}\n\n{context_str}"
        
        # Tenter d'envoyer sur tous les canaux disponibles
        success = False
        
        # Ntfy
        if self._send_ntfy(level, full_message, title):
            success = True
        
        # Pushover (si critical ou error)
        if level in [AlertLevel.CRITICAL, AlertLevel.ERROR]:
            if self._send_pushover(level, full_message, title):
                success = True
        
        # Fallback : toujours écrire dans le fichier
        self._write_fallback(level, message, context or {})
        
        # Statistiques
        if success:
            self.stats["sent"] += 1
        else:
            self.stats["failed"] += 1
        
        # Log local
        log_method = {
            AlertLevel.INFO: logger.info,
            AlertLevel.WARNING: logger.warning,
            AlertLevel.ERROR: logger.error,
            AlertLevel.CRITICAL: logger.critical
        }.get(level, logger.info)
        
        log_method(f"ALERT: {message}")
    
    def alert_exception(
        self,
        exception: Exception,
        context: Optional[Dict[str, Any]] = None
    ):
        """
        Alerte pour une exception non gérée
        
        Args:
            exception: Exception capturée
            context: Contexte additionnel
        """
        tb = traceback.format_exc()
        message = f"Exception non gérée: {type(exception).__name__}\n{str(exception)}\n\n{tb}"
        
        self.alert(
            AlertLevel.CRITICAL,
            message,
            context=context,
            title="BotCélian - CRASH"
        )
    
    def alert_long_execution(self, duration: float, threshold: float = 600):
        """
        Alerte si l'exécution est trop longue
        
        Args:
            duration: Durée en secondes
            threshold: Seuil d'alerte en secondes
        """
        if duration > threshold:
            self.alert(
                AlertLevel.WARNING,
                f"Exécution longue détectée: {duration:.0f}s (seuil: {threshold:.0f}s)",
                context={"duration": duration, "threshold": threshold},
                title="BotCélian - Exécution longue"
            )
    
    def alert_api_error(
        self,
        api_name: str,
        error: str,
        retry_count: int = 0
    ):
        """
        Alerte pour erreur API
        
        Args:
            api_name: Nom de l'API (Mistral, Pywikibot, etc.)
            error: Message d'erreur
            retry_count: Nombre de tentatives
        """
        level = AlertLevel.ERROR if retry_count >= 3 else AlertLevel.WARNING
        
        self.alert(
            level,
            f"Erreur API {api_name}: {error}",
            context={
                "api": api_name,
                "retry_count": retry_count,
                "error": error
            },
            title=f"BotCélian - Erreur {api_name}"
        )
    
    def alert_infinite_loop(self, context: Optional[Dict[str, Any]] = None):
        """
        Alerte pour boucle infinie détectée
        
        Args:
            context: Contexte de la boucle
        """
        self.alert(
            AlertLevel.CRITICAL,
            "Boucle anormale détectée - arrêt du script recommandé",
            context=context,
            title="BotCélian - BOUCLE INFINIE"
        )
    
    def get_stats(self) -> Dict[str, int]:
        """Retourne les statistiques d'alertes"""
        return self.stats.copy()


# Singleton global
_alerting_instance = None


def get_alerting(
    ntfy_topic: Optional[str] = None,
    pushover_token: Optional[str] = None,
    pushover_user: Optional[str] = None,
    enabled: bool = True
) -> AlertingSystem:
    """
    Récupère l'instance singleton du système d'alertes
    
    Args:
        ntfy_topic: Topic Ntfy
        pushover_token: Token Pushover
        pushover_user: User Pushover
        enabled: Activer les alertes
        
    Returns:
        Instance d'AlertingSystem
    """
    global _alerting_instance
    if _alerting_instance is None:
        _alerting_instance = AlertingSystem(
            ntfy_topic=ntfy_topic,
            pushover_token=pushover_token,
            pushover_user=pushover_user,
            enabled=enabled
        )
    return _alerting_instance


# Fonctions helper
def alert(level: AlertLevel, message: str, context: Optional[Dict[str, Any]] = None):
    """Helper pour alert()"""
    alerting = get_alerting()
    alerting.alert(level, message, context)


def alert_exception(exception: Exception, context: Optional[Dict[str, Any]] = None):
    """Helper pour alert_exception()"""
    alerting = get_alerting()
    alerting.alert_exception(exception, context)


def alert_api_error(api_name: str, error: str, retry_count: int = 0):
    """Helper pour alert_api_error()"""
    alerting = get_alerting()
    alerting.alert_api_error(api_name, error, retry_count)