#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Module de reporting (Discord, logs, wiki)
"""

import logging
import urllib.parse
from datetime import datetime, timezone
import requests

logger = logging.getLogger(__name__)


class DiscordReporter:
    """Gère les notifications Discord"""
    
    def __init__(self, webhook_url, timeout=10):
        """
        Args:
            webhook_url: URL du webhook Discord
            timeout: Timeout des requêtes en secondes
        """
        self.webhook_url = webhook_url
        self.timeout = timeout
    
    def send_embed(self, embed, mentions=""):
        """
        Envoie un embed Discord
        
        Args:
            embed: Dictionnaire de l'embed
            mentions: Mentions utilisateurs (optionnel)
            
        Returns:
            bool: True si succès
        """
        if not self.webhook_url:
            logger.warning("Webhook Discord non configuré")
            return False
        
        payload = {
            "content": mentions,
            "embeds": [embed]
        }
        
        try:
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            logger.debug(f"Embed Discord envoyé: {embed.get('title', 'Sans titre')}")
            return True
            
        except requests.exceptions.Timeout:
            logger.error("Timeout webhook Discord")
            return False
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Erreur webhook Discord: {e}")
            return False
    
    def report_analysis(self, title, url, result, actions, is_si=False):
        """
        Envoie un rapport d'analyse standard
        
        Args:
            title: Titre de la page
            url: URL de la page
            result: Résultat de l'analyse IA
            actions: Liste des actions effectuées
            is_si: Si un SI a été ajouté
            
        Returns:
            bool: True si succès
        """
        embed = {
            "title": f"🤖 Analyse IA : {title}",
            "url": url,
            "description": (
                f"**SI** : {'✅ Oui' if is_si else '❌ Non'}\n"
                f"**Vandalisme** : {'✅' if result['vandalisme'] else '❌'}\n"
                f"**Langue FR** : {'✅' if result['langue_fr'] else '❌'}\n"
                f"**Autopromo** : {'✅' if result['autopromo'] else '❌'}\n"
                f"**Qualité** : {result['qualite']}\n"
                f"**Confiance** : {result['confiance']}/100\n\n"
                f"🧠 **Justification** : {result['justification']}\n"
                f"🛠 **Actions** : {', '.join(actions) if actions else 'Aucune'}"
            ),
            "color": 0x3498DB,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return self.send_embed(embed)
    
    def report_si(self, title, url, mentions=""):
        """
        Envoie une alerte SI (Suppression Immédiate)
        
        Args:
            title: Titre de la page
            url: URL de la page
            mentions: Utilisateurs à mentionner
            
        Returns:
            bool: True si succès
        """
        embed = {
            "title": f"🚨 SI ajouté : {title}",
            "url": url,
            "description": "⚠️ Page détectée avec SI. Vérifier et supprimer si nécessaire.",
            "color": 0xFF0000,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return self.send_embed(embed, mentions=mentions)
    
    def report_error(self, error_msg, context=""):
        """
        Envoie un rapport d'erreur
        
        Args:
            error_msg: Message d'erreur
            context: Contexte de l'erreur
            
        Returns:
            bool: True si succès
        """
        embed = {
            "title": "❌ Erreur Bot",
            "description": f"**Erreur** : {error_msg}\n\n**Contexte** : {context}",
            "color": 0xFF6B6B,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        return self.send_embed(embed)


class WikiLogger:
    """Gère les logs sur une page wiki"""
    
    def __init__(self, site, log_page_title):
        """
        Args:
            site: Site pywikibot
            log_page_title: Titre de la page de logs
        """
        self.site = site
        self.log_page_title = log_page_title
        self.entries = []
    
    def add_entry(self, title, result, actions, is_si=False):
        """
        Ajoute une entrée de log
        
        Args:
            title: Titre de la page
            result: Résultat de l'analyse IA
            actions: Liste des actions
            is_si: Si un SI a été ajouté
        """
        entry = (
            f"* '''{title}'''\n"
            f"  * SI : {'Oui' if is_si else 'Non'}\n"
            f"  * Vandalisme : {result['vandalisme']}\n"
            f"  * Langue FR : {result['langue_fr']}\n"
            f"  * Autopromo : {result['autopromo']}\n"
            f"  * Qualité : {result['qualite']}\n"
            f"  * Confiance : {result['confiance']}/100\n"
            f"  * Actions : {', '.join(actions) if actions else 'Aucune'}\n"
            f"  * Justification : {result['justification']}"
        )
        self.entries.append(entry)
        logger.debug(f"Entrée log ajoutée pour: {title}")
    
    def save_to_wiki(self, bot_name, duration, start_time=None):
        """
        Sauvegarde les logs sur la page wiki
        
        Args:
            bot_name: Nom du bot
            duration: Durée d'exécution en secondes
            start_time: Heure de début (optionnel)
            
        Returns:
            bool: True si succès
        """
        if not self.entries:
            logger.info("Aucune entrée à sauvegarder")
            return False
        
        try:
            import pywikibot
            log_page = pywikibot.Page(self.site, self.log_page_title)
            
            # Récupérer le contenu existant
            old_text = log_page.text if log_page.exists() else ""
            
            # Préparer le nouveau résumé
            now = start_time or datetime.now(timezone.utc)
            date_str = now.strftime("%d/%m/%Y")
            heure_str = now.strftime("%H:%M:%S")
            
            resume = f"""{{{{Utilisateur:{bot_name}/Resume
| script = rapport
| date = {date_str}
| heure = {heure_str}
| durée = {duration}s
| modifs = {len(self.entries)}
| autres =
{chr(10).join(self.entries)}
}}}}"""
            
            # Ajouter le nouveau résumé
            log_page.text = old_text.rstrip() + "\n\n" + resume
            log_page.save(f"📝 {bot_name} : rapport IA", minor=True)
            
            logger.info(f"Logs sauvegardés sur {self.log_page_title} ({len(self.entries)} entrées)")
            return True
            
        except Exception as e:
            logger.error(f"Erreur sauvegarde logs wiki: {e}")
            return False
    
    def clear(self):
        """Efface les entrées en mémoire"""
        self.entries.clear()


def format_wiki_url(title, base_url="https://fr.vikidia.org/wiki/"):
    """
    Formate une URL wiki
    
    Args:
        title: Titre de la page
        base_url: URL de base du wiki
        
    Returns:
        str: URL complète
    """
    encoded_title = urllib.parse.quote(title.replace(' ', '_'))
    return f"{base_url}{encoded_title}"


def discord_embed(webhook_url, embed, mentions=""):
    """
    Fonction helper pour envoyer un embed Discord
    
    Args:
        webhook_url: URL du webhook
        embed: Dictionnaire de l'embed
        mentions: Mentions (optionnel)
        
    Returns:
        bool: True si succès
    """
    reporter = DiscordReporter(webhook_url)
    return reporter.send_embed(embed, mentions)