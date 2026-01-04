#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de logging structuré JSON pour analyses et statistiques
"""

import os
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger(__name__)


class StructuredLogger:
    """Gère les logs structurés au format JSON Lines"""
    
    def __init__(self, log_dir="logs"):
        """
        Args:
            log_dir: Répertoire des logs
        """
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.current_file = None
        self.current_month = None
    
    def _get_log_file(self):
        """
        Récupère le fichier de log du mois courant
        
        Returns:
            Path: Chemin du fichier de log
        """
        now = datetime.now(timezone.utc)
        month_str = now.strftime("%Y-%m")
        
        # Changer de fichier si nouveau mois
        if month_str != self.current_month:
            self.current_month = month_str
            self.current_file = self.log_dir / f"{month_str}.jsonl"
            logger.info(f"Fichier de log: {self.current_file}")
        
        return self.current_file
    
    def log_event(
        self,
        script: str,
        page: str,
        actions: List[str],
        is_si: bool = False,
        confiance: int = 0,
        qualite: str = "moyenne",
        problemes: Optional[List[str]] = None,
        resume: str = "",
        extra: Optional[Dict[str, Any]] = None
    ):
        """
        Enregistre un événement structuré
        
        Args:
            script: Nom du script (rapport, averto, etc.)
            page: Titre de la page traitée
            actions: Liste des actions effectuées
            is_si: Si un SI a été ajouté
            confiance: Score de confiance IA (0-100)
            qualite: Qualité détectée (bonne/moyenne/mauvaise)
            problemes: Liste des problèmes détectés
            resume: Résumé court de l'action
            extra: Données additionnelles optionnelles
        """
        event = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "script": script,
            "page": page,
            "action": actions,
            "si": is_si,
            "confiance": confiance,
            "qualite": qualite,
            "problemes": problemes or [],
            "resume": resume
        }
        
        # Ajouter données extra si présentes
        if extra:
            event.update(extra)
        
        try:
            log_file = self._get_log_file()
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
            logger.debug(f"Événement loggé: {page}")
        except Exception as e:
            logger.error(f"Erreur écriture log structuré: {e}")
    
    def load_logs(
        self,
        month: Optional[str] = None,
        script: Optional[str] = None,
        si_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Charge les logs avec filtres optionnels
        
        Args:
            month: Mois au format YYYY-MM (None = mois courant)
            script: Filtrer par script
            si_only: Uniquement les événements SI
            
        Returns:
            Liste d'événements
        """
        if month is None:
            month = datetime.now(timezone.utc).strftime("%Y-%m")
        
        log_file = self.log_dir / f"{month}.jsonl"
        
        if not log_file.exists():
            logger.warning(f"Fichier de log inexistant: {log_file}")
            return []
        
        events = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    
                    try:
                        event = json.loads(line)
                        
                        # Filtres
                        if script and event.get("script") != script:
                            continue
                        if si_only and not event.get("si", False):
                            continue
                        
                        events.append(event)
                    except json.JSONDecodeError as e:
                        logger.error(f"Ligne JSON invalide: {e}")
            
            logger.info(f"Chargé {len(events)} événements depuis {log_file}")
            return events
            
        except Exception as e:
            logger.error(f"Erreur lecture logs: {e}")
            return []
    
    def aggregate_stats(
        self,
        month: Optional[str] = None,
        script: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Agrège les statistiques des logs
        
        Args:
            month: Mois à analyser (None = mois courant)
            script: Filtrer par script
            
        Returns:
            Dictionnaire de statistiques
        """
        events = self.load_logs(month=month, script=script)
        
        if not events:
            return {
                "total_events": 0,
                "pages_uniques": 0,
                "si_total": 0,
                "actions": {},
                "qualite": {},
                "problemes": {},
                "confiance_moyenne": 0,
                "scripts": {}
            }
        
        # Compteurs
        pages = set()
        si_count = 0
        action_counts = defaultdict(int)
        qualite_counts = defaultdict(int)
        probleme_counts = defaultdict(int)
        script_counts = defaultdict(int)
        confiances = []
        
        for event in events:
            pages.add(event.get("page", ""))
            
            if event.get("si", False):
                si_count += 1
            
            # Actions
            for action in event.get("action", []):
                action_counts[action] += 1
            
            # Qualité
            qualite = event.get("qualite", "inconnue")
            qualite_counts[qualite] += 1
            
            # Problèmes
            for probleme in event.get("problemes", []):
                probleme_counts[probleme] += 1
            
            # Scripts
            script_name = event.get("script", "unknown")
            script_counts[script_name] += 1
            
            # Confiance
            confiance = event.get("confiance", 0)
            if confiance > 0:
                confiances.append(confiance)
        
        # Calculs
        confiance_moyenne = (
            sum(confiances) / len(confiances) if confiances else 0
        )
        
        stats = {
            "total_events": len(events),
            "pages_uniques": len(pages),
            "si_total": si_count,
            "si_percentage": round((si_count / len(events)) * 100, 2) if events else 0,
            "actions": dict(action_counts),
            "qualite": dict(qualite_counts),
            "problemes": dict(probleme_counts),
            "scripts": dict(script_counts),
            "confiance_moyenne": round(confiance_moyenne, 2),
            "periode": month or datetime.now(timezone.utc).strftime("%Y-%m")
        }
        
        return stats
    
    def get_top_pages(
        self,
        month: Optional[str] = None,
        limit: int = 10,
        si_only: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Récupère les pages les plus traitées
        
        Args:
            month: Mois à analyser
            limit: Nombre maximum de résultats
            si_only: Uniquement les pages avec SI
            
        Returns:
            Liste des pages avec compteurs
        """
        events = self.load_logs(month=month, si_only=si_only)
        
        page_counts = defaultdict(lambda: {
            "count": 0,
            "si": 0,
            "actions": [],
            "last_event": None
        })
        
        for event in events:
            page = event.get("page", "")
            page_counts[page]["count"] += 1
            
            if event.get("si", False):
                page_counts[page]["si"] += 1
            
            page_counts[page]["actions"].extend(event.get("action", []))
            page_counts[page]["last_event"] = event.get("timestamp")
        
        # Trier par nombre d'événements
        sorted_pages = sorted(
            page_counts.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:limit]
        
        return [
            {
                "page": page,
                "count": data["count"],
                "si_count": data["si"],
                "actions": list(set(data["actions"])),
                "last_event": data["last_event"]
            }
            for page, data in sorted_pages
        ]
    
    def export_stats_json(
        self,
        output_file: str,
        month: Optional[str] = None
    ):
        """
        Exporte les statistiques en JSON pour site web
        
        Args:
            output_file: Fichier de sortie
            month: Mois à exporter
        """
        stats = self.aggregate_stats(month=month)
        top_pages = self.get_top_pages(month=month, limit=20)
        
        export_data = {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "periode": month or datetime.now(timezone.utc).strftime("%Y-%m"),
            "stats": stats,
            "top_pages": top_pages
        }
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)
            logger.info(f"Stats exportées: {output_file}")
        except Exception as e:
            logger.error(f"Erreur export stats: {e}")


# Singleton global
_logger_instance = None


def get_logger(log_dir="logs") -> StructuredLogger:
    """
    Récupère l'instance singleton du logger structuré
    
    Args:
        log_dir: Répertoire des logs
        
    Returns:
        Instance de StructuredLogger
    """
    global _logger_instance
    if _logger_instance is None:
        _logger_instance = StructuredLogger(log_dir)
    return _logger_instance


# Fonctions helper
def log_event(**kwargs):
    """Helper pour log_event"""
    logger = get_logger()
    logger.log_event(**kwargs)


def load_logs(**kwargs):
    """Helper pour load_logs"""
    logger = get_logger()
    return logger.load_logs(**kwargs)


def aggregate_stats(**kwargs):
    """Helper pour aggregate_stats"""
    logger = get_logger()
    return logger.aggregate_stats(**kwargs)