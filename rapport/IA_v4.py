#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module d'analyse IA V4 avec décision ébauche fine
"""

import json
import re
import time
import logging
from mistralai import Mistral

logger = logging.getLogger(__name__)


class IAAnalyzerV4:
    """Analyse IA avec décision ébauche et portails"""
    
    def __init__(self, api_key, model="mistral-small-latest", max_retries=3):
        self.api_key = api_key
        self.model = model
        self.max_retries = max_retries
        self.client = None
        self.last_call_time = 0
        self.min_call_interval = 2
    
    def _rate_limit(self):
        """Rate limiting"""
        elapsed = time.time() - self.last_call_time
        if elapsed < self.min_call_interval:
            time.sleep(self.min_call_interval - elapsed)
        self.last_call_time = time.time()
    
    def _get_client(self):
        """Récupère client Mistral"""
        if self.client is None:
            self.client = Mistral(api_key=self.api_key)
        return self.client
    
    def _extract_json(self, text: str) -> dict:
        """Extrait JSON de la réponse"""
        # Chercher bloc JSON
        match = re.search(r'\{[^\}]*\}', text, re.S)
        if not match:
            raise ValueError("Aucun JSON trouvé")
        
        return json.loads(match.group(0))
    
    def _validate_response(self, data: dict) -> dict:
        """Valide et normalise la réponse IA"""
        required = [
            "vandalisme", "langue_fr", "autopromo", 
            "qualite", "confiance", "justification",
            "needs_stub", "stub_confidence", "portails"
        ]
        
        for key in required:
            if key not in data:
                raise ValueError(f"Clé manquante: {key}")
        
        # Normaliser booléens
        data["vandalisme"] = bool(data["vandalisme"])
        data["langue_fr"] = bool(data["langue_fr"])
        data["autopromo"] = bool(data["autopromo"])
        data["needs_stub"] = bool(data["needs_stub"])
        
        # Normaliser qualité
        valid_qualities = ["bonne", "moyenne", "mauvaise"]
        if data["qualite"].lower() not in valid_qualities:
            logger.warning(f"Qualité invalide: {data['qualite']}")
            data["qualite"] = "moyenne"
        else:
            data["qualite"] = data["qualite"].lower()
        
        # Normaliser confiances (0-100)
        data["confiance"] = max(0, min(100, int(float(data.get("confiance", 0)))))
        data["stub_confidence"] = max(0, min(100, int(float(data.get("stub_confidence", 0)))))
        
        # Normaliser portails (liste)
        if not isinstance(data["portails"], list):
            data["portails"] = []
        
        # Limiter justification
        if len(data["justification"]) > 500:
            data["justification"] = data["justification"][:497] + "..."
        
        return data
    
    def _get_fallback_response(self, error_msg="Analyse IA indisponible") -> dict:
        """Réponse par défaut en cas d'erreur"""
        return {
            "vandalisme": False,
            "langue_fr": True,
            "autopromo": False,
            "qualite": "moyenne",
            "confiance": 0,
            "justification": error_msg,
            "needs_stub": False,
            "stub_confidence": 0,
            "portails": []
        }
    
    def analyze(self, text: str, title: str = "") -> dict:
        """
        Analyse complète avec décision ébauche
        
        Args:
            text: Texte de l'article
            title: Titre de l'article
            
        Returns:
            dict avec toutes les analyses
        """
        if not text or not text.strip():
            return self._get_fallback_response("Texte vide")
        
        text_sample = text[:4000]
        
        prompt = f"""Analyse cet article Vikidia.
Réponds UNIQUEMENT par un JSON valide, sans commentaire.

Titre : {title}

Clés requises :
- vandalisme (bool) : contenu offensant, destruction, spam
- langue_fr (bool) : article en français
- autopromo (bool) : promotion commerciale/personnelle
- qualite (string) : "bonne", "moyenne" ou "mauvaise"
- confiance (number 0-100) : certitude générale
- justification (string max 200 mots) : explication

NOUVEAU - Décision ébauche :
- needs_stub (bool) : l'article est-il une ébauche ?
  * true si : très court, peu d'infos, incomplet
  * false si : développé, structuré, plusieurs sections
- stub_confidence (number 0-100) : certitude de la décision ébauche
- portails (array of strings) : portails pertinents
  Exemples : ["Histoire", "Géographie", "Sciences", "Arts", "Biographie", "Sport", "Littérature"]
  Maximum 3 portails. Liste vide si aucun ne convient.

Texte :
{text_sample}"""
        
        for attempt in range(self.max_retries):
            try:
                self._rate_limit()
                
                client = self._get_client()
                response = client.chat.complete(
                    model=self.model,
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.2
                )
                
                raw = response.choices[0].message.content.strip()
                logger.debug(f"Réponse IA brute: {raw[:200]}")
                
                data = self._extract_json(raw)
                data = self._validate_response(data)
                
                logger.info(
                    f"Analyse IA OK - confiance: {data['confiance']}%, "
                    f"ébauche: {data['needs_stub']} ({data['stub_confidence']}%)"
                )
                return data
                
            except json.JSONDecodeError as e:
                logger.error(f"Erreur JSON (tentative {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    
            except ValueError as e:
                logger.error(f"Erreur validation (tentative {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
                    
            except Exception as e:
                logger.error(f"Erreur API (tentative {attempt + 1}): {e}")
                if attempt < self.max_retries - 1:
                    time.sleep(2 ** attempt)
        
        logger.error("Échec analyse IA après toutes tentatives")
        return self._get_fallback_response("Erreur API")
    
    def close(self):
        """Ferme le client"""
        if self.client:
            try:
                self.client.close()
            except Exception as e:
                logger.error(f"Erreur fermeture: {e}")
            finally:
                self.client = None


def analyse_mistral(text: str, api_key: str, title: str = "") -> dict:
    """Helper pour compatibilité"""
    analyzer = IAAnalyzerV4(api_key)
    try:
        return analyzer.analyze(text, title)
    finally:
        analyzer.close()


# Alias pour compatibilité
class IAAnalyzer(IAAnalyzerV4):
    """Alias pour compatibilité"""
    pass