#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
BotCélian V4 - Corrections critiques et amélioration IA
"""

import os
import sys
import json
import re
import time
import logging
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

import pywikibot
from pywikibot.data.api import Request

# Modules V4
from typo_v4 import SafeTypoFixer
from maintenance_v4 import MaintenanceDetectorV4
from IA_v4 import IAAnalyzerV4
from reporter import DiscordReporter, WikiLogger, format_wiki_url

# Nouvelles briques
from structured_logging import get_logger as get_structured_logger
from alerting import get_alerting, AlertLevel
from si_notifications import SIDetector, get_notifier as get_si_notifier
from averto import AvertoDetector
from sensitive_terms import get_detector as get_sensitive_detector

# Configuration
from config_updated import *

# ================= LOGGING =================
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(LOG_DIR, "rapport_v4.log"), encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# ================= MONITORING =================
@contextmanager
def execution_monitor(alerting):
    start_time = time.time()
    try:
        yield
    except KeyboardInterrupt:
        logger.info("Interruption utilisateur")
        alerting.alert(AlertLevel.WARNING, "Bot interrompu", title="Interruption")
        raise
    except Exception as e:
        logger.error(f"Exception: {e}", exc_info=True)
        alerting.alert_exception(e, context={"location": "main"})
        raise
    finally:
        duration = time.time() - start_time
        if duration > ALERT_EXECUTION_TIME_THRESHOLD:
            alerting.alert_long_execution(duration, ALERT_EXECUTION_TIME_THRESHOLD)

# ================= STATE =================
class StateManager:
    def __init__(self, state_file):
        self.state_file = state_file
        self.seen_pages = set()
    
    def load(self):
        if os.path.exists(self.state_file):
            try:
                with open(self.state_file, 'r', encoding='utf-8') as f:
                    self.seen_pages = set(json.load(f))
                logger.info(f"État chargé: {len(self.seen_pages)} pages")
            except json.JSONDecodeError:
                logger.warning("state.json corrompu")
                self.seen_pages = set()
    
    def save(self):
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(self.seen_pages), f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Erreur save state: {e}")
    
    def is_seen(self, title):
        return title in self.seen_pages
    
    def mark_seen(self, title):
        self.seen_pages.add(title)

# ================= UTILS =================
def is_redirect(page, text):
    return page.isRedirectPage() or bool(re.match(r'\s*#\s*(redirect|redirection)', text, re.I))

def get_new_pages(site):
    now = datetime.now(timezone.utc)
    past = now - timedelta(minutes=RC_LOOKBACK_MINUTES)
    
    req = Request(site=site, parameters={
        "action": "query",
        "list": "recentchanges",
        "rctype": "new",
        "rcnamespace": [0, 2],
        "rcstart": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rcend": past.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "rclimit": RC_LIMIT,
        "rcprop": "title|user"
    })
    
    try:
        result = req.submit()
        pages = [(pywikibot.Page(site, rc["title"]), rc.get("user", "")) 
                 for rc in result["query"]["recentchanges"]]
        logger.info(f"{len(pages)} nouvelles pages")
        return pages
    except Exception as e:
        logger.error(f"Erreur get pages: {e}")
        return []

# ================= PROCESSEUR V4 =================
class PageProcessorV4:
    """Processeur V4 avec tous les correctifs"""
    
    def __init__(self, site, bot_name, components):
        self.site = site
        self.bot_name = bot_name
        self.components = components
        self.stats = {
            "analyzed": 0,
            "si_added": 0,
            "typo_fixed": 0,
            "maintenance_added": 0,
            "stub_added": 0,
            "averto_detected": 0,
            "sensitive_detected": 0,
            "in_progress_skipped": 0,
            "errors": 0
        }
        self.edit_count = 0
    
    def process(self, page, creator=""):
        """Traite une page avec tous les correctifs V4"""
        title = page.title()
        logger.info(f"=== Traitement: {title} ===")
        
        try:
            # Limite éditions
            if self.edit_count >= MAX_EDITS_PER_RUN:
                logger.warning(f"⚠️ Limite éditions atteinte ({MAX_EDITS_PER_RUN})")
                return False, []
            
            text = page.text
            
            # Redirection
            if is_redirect(page, text):
                logger.info("→ Redirection ignorée")
                return False, []
            
            # 🚨 BUG FIX 2: Vérifier si en travaux
            if self.components["maintenance"].is_in_progress(text):
                logger.info("→ Page en travaux, IGNORÉE")
                self.stats["in_progress_skipped"] += 1
                # Log structuré
                if STRUCTURED_LOGS_ENABLED:
                    self.components["structured_logger"].log_event(
                        script="rapport",
                        page=title,
                        actions=["ignoré"],
                        resume="Page en travaux"
                    )
                return False, []
            
            actions = []
            is_si = False
            si_reason = ""
            
            # 🔍 ÉTAPE 1: Termes sensibles (prioritaire)
            if SENSITIVE_TERMS_ENABLED:
                matches, max_severity = self.components["sensitive"].detect(text, title)
                if matches:
                    self.stats["sensitive_detected"] += 1
                    should_si, _, reason = self.components["sensitive"].should_add_si(
                        text, title, severity_threshold=SENSITIVE_TERMS_SI_THRESHOLD
                    )
                    if should_si and ENABLE_SI_AUTO:
                        if self._add_si_template(page, text, reason):
                            actions.append("SI termes sensibles")
                            is_si = True
                            si_reason = reason
                            self.stats["si_added"] += 1
            
            # 🔍 ÉTAPE 2: Averto (copie)
            if not is_si and AVERTO_ENABLED:
                decision = self.components["averto"].detect(title, text, creator)
                if decision.action in ["si", "warning"]:
                    self.stats["averto_detected"] += 1
                    if decision.action == "si" and ENABLE_SI_AUTO:
                        reason = f"copie ({decision.sources[0].source_name})"
                        if self._add_si_template(page, text, reason):
                            actions.append(f"SI {reason}")
                            is_si = True
                            si_reason = reason
                            self.stats["si_added"] += 1
            
            # 🔍 ÉTAPE 3: Analyse IA
            result = None
            if not is_si:
                result = self.components["ia"].analyze(text, title)
                self.stats["analyzed"] += 1
                
                # Détection SI depuis IA
                si_decision = SIDetector.from_ia_result(result)
                if si_decision and si_decision.should_add_si and ENABLE_SI_AUTO:
                    reason_text = si_decision.reason.value
                    if si_decision.confidence > 0:
                        reason_text += f" <small>(confiance : {si_decision.confidence}/100)</small>"
                    
                    if self._add_si_template(page, text, reason_text):
                        actions.append(f"SI {si_decision.reason.value}")
                        is_si = True
                        si_reason = reason_text
                        self.stats["si_added"] += 1
                        
                        # Notification SI
                        if SI_NOTIFICATIONS_ENABLED:
                            self.components["si_notifier"].notify(title, si_decision)
            
            # ✅ ACTIONS NON-SI
            if not is_si:
                # Typo (V4 sécurisé)
                if ENABLE_TYPO_AUTO:
                    if self._fix_typo_safe(page):
                        actions.append("typo")
                        self.stats["typo_fixed"] += 1
                        text = page.text
                
                # Maintenance
                if ENABLE_MAINTENANCE_AUTO:
                    if self._add_maintenance(page, text):
                        actions.append("maintenance")
                        self.stats["maintenance_added"] += 1
                        text = page.text
                
                # 🚨 BUG FIX 3: Ébauche V4 avec portails et IA
                if self._add_stub_intelligent(page, text, result):
                    actions.append("ébauche")
                    self.stats["stub_added"] += 1
            
            # Logs structurés
            if STRUCTURED_LOGS_ENABLED and (actions or result):
                problems = self.components["maintenance"].detect_problems(text)
                result_data = result if result else self.components["ia"]._get_fallback_response()
                self.components["structured_logger"].log_event(
                    script="rapport",
                    page=title,
                    actions=actions,
                    is_si=is_si,
                    confiance=result_data.get("confiance", 0),
                    qualite=result_data.get("qualite", "moyenne"),
                    problemes=problems,
                    resume=result_data.get("justification", "")
                )
            
            # Rapports Discord
            if actions and not DRY_RUN:
                url = format_wiki_url(title)
                result_data = result if result else self.components["ia"]._get_fallback_response()
                self.components["discord"].report_analysis(title, url, result_data, actions, is_si)
                self.components["wiki_logger"].add_entry(title, result_data, actions, is_si)
            
            logger.info(f"✅ Actions: {', '.join(actions) if actions else 'aucune'}")
            return True, actions
            
        except Exception as e:
            logger.error(f"❌ Erreur: {e}", exc_info=True)
            self.stats["errors"] += 1
            self.components["alerting"].alert_exception(e, context={"page": title})
            return False, []
    
    def _add_si_template(self, page, text, reason):
        """Ajoute SI"""
        if DRY_RUN:
            logger.info(f"[DRY] SI: {reason}")
            return True
        
        try:
            # 🚨 BUG FIX 1: Vérifier si SI déjà présent
            if re.search(r'\{\{\s*SI\s*\|', text, re.I):
                logger.warning("⚠️ SI déjà présent, pas d'ajout")
                return False
            
            new_text = f"{{{{SI|{reason}|{self.bot_name}}}}}\n{text}"
            page.text = new_text
            page.save(f"SI {reason.split()[0]}")
            self.edit_count += 1
            logger.info(f"→ SI ajouté: {reason}")
            return True
        except Exception as e:
            logger.error(f"→ Erreur SI: {e}")
            return False
    
    def _fix_typo_safe(self, page):
        """🚨 BUG FIX 4: Typo SÉCURISÉ"""
        if DRY_RUN:
            return False
        
        try:
            original_text = page.text
            fixed_text = self.components["typo"].fix(original_text)
            
            # Vérifier si changé
            if fixed_text == original_text:
                return False
            
            # Vérifier intégrité (doublement sécurisé)
            if len(fixed_text) < len(original_text) * 0.95:
                logger.warning("⚠️ Typo a réduit trop le texte - ANNULÉ")
                return False
            
            summary = self.components["typo"].get_summary(original_text, fixed_text)
            page.text = fixed_text
            page.save(summary)
            self.edit_count += 1
            logger.info(f"→ Typo OK: {summary}")
            return True
            
        except Exception as e:
            logger.error(f"→ Erreur typo: {e}")
            return False
    
    def _add_maintenance(self, page, text):
        """Ajoute maintenance"""
        if DRY_RUN:
            return False
        
        try:
            problems = self.components["maintenance"].detect_problems(text)
            if not problems:
                return False
            
            # 🚨 BUG FIX 1: Vérifier si déjà présent
            if self.components["maintenance"].has_template(text, "Maintenance"):
                logger.info("→ Maintenance déjà présente")
                return False
            
            if self.components["maintenance"].needs_maintenance_template(text, problems):
                new_text = self.components["maintenance"].add_maintenance_template(text, problems)
                summary = self.components["maintenance"].get_maintenance_summary(problems)
                page.text = new_text
                page.save(summary)
                self.edit_count += 1
                logger.info(f"→ Maintenance: {', '.join(problems)}")
                return True
            return False
        except Exception as e:
            logger.error(f"→ Erreur maintenance: {e}")
            return False
    
    def _add_stub_intelligent(self, page, text, ia_result):
        """🚨 BUG FIX 3: Ébauche V4 avec portails et IA"""
        if DRY_RUN:
            return False
        
        try:
            # Décision intelligente
            needs_stub, portals, reason = self.components["maintenance"].needs_stub_template(
                text, ia_result
            )
            
            if not needs_stub:
                logger.debug(f"→ Pas d'ébauche: {reason}")
                return False
            
            # 🚨 BUG FIX 1: Vérifier si déjà présent
            if self.components["maintenance"].has_template(text, "Ébauche") or \
               self.components["maintenance"].has_template(text, "ébauche"):
                logger.info("→ Ébauche déjà présente")
                return False
            
            new_text = self.components["maintenance"].add_stub_template(text, portals)
            summary = self.components["maintenance"].get_stub_summary(portals)
            page.text = new_text
            page.save(summary)
            self.edit_count += 1
            logger.info(f"→ Ébauche ajoutée: {reason}")
            if portals:
                logger.info(f"   Portails: {', '.join(portals)}")
            return True
            
        except Exception as e:
            logger.error(f"→ Erreur ébauche: {e}")
            return False
    
    def get_stats(self):
        return self.stats.copy()

# ================= MAIN =================
def main():
    start_time = time.time()
    start_datetime = datetime.now(timezone.utc)
    
    logger.info("=" * 70)
    logger.info(f"🤖 BotCélian V4 - Mode: {'DRY RUN ⚠️' if DRY_RUN else 'PRODUCTION ✅'}")
    logger.info("=" * 70)
    
    # Validation config
    try:
        validate_config()
    except ValueError as e:
        logger.error(str(e))
        return 1
    
    # Alerting
    alerting = get_alerting(
        ntfy_topic=NTFY_TOPIC if ALERTING_ENABLED else None,
        pushover_token=PUSHOVER_TOKEN,
        pushover_user=PUSHOVER_USER,
        enabled=ALERTING_ENABLED
    )
    
    with execution_monitor(alerting):
        # Wiki
        try:
            site = pywikibot.Site("fr", "vikidia")
            site.login()
            logger.info("✅ Wiki connecté")
        except Exception as e:
            logger.error(f"❌ Connexion wiki: {e}")
            alerting.alert_api_error("Pywikibot", str(e))
            return 1
        
        # Composants V4
        components = {
            "ia": IAAnalyzerV4(MISTRAL_API_KEY, model=MISTRAL_MODEL, max_retries=MISTRAL_MAX_RETRIES),
            "typo": SafeTypoFixer(),
            "maintenance": MaintenanceDetectorV4(min_words_stub=MIN_WORDS_STUB),
            "discord": DiscordReporter(DISCORD_WEBHOOK),
            "wiki_logger": WikiLogger(site, f"Utilisateur:{BOT_NAME}/Logs/{LOG_PAGE_YEAR}"),
            "structured_logger": get_structured_logger(STRUCTURED_LOGS_DIR),
            "alerting": alerting,
            "si_notifier": get_si_notifier(
                discord_webhook=DISCORD_WEBHOOK if SI_NOTIFICATIONS_ENABLED else None,
                ntfy_topic=SI_NTFY_TOPIC,
                enabled=SI_NOTIFICATIONS_ENABLED,
                user_mentions=SI_USER_MENTIONS
            ),
            "averto": AvertoDetector(
                similarity_threshold=AVERTO_SIMILARITY_THRESHOLD,
                min_text_length=AVERTO_MIN_TEXT_LENGTH,
                check_wikipedia=AVERTO_CHECK_WIKIPEDIA,
                check_wikimini=AVERTO_CHECK_WIKIMINI
            ) if AVERTO_ENABLED else None,
            "sensitive": get_sensitive_detector(SENSITIVE_TERMS_CONFIG) if SENSITIVE_TERMS_ENABLED else None
        }
        
        # État
        state = StateManager("state.json")
        state.load()
        
        # Processeur V4
        processor = PageProcessorV4(site, BOT_NAME, components)
        
        # Pages
        pages_data = get_new_pages(site)
        
        # Traitement
        for page, creator in pages_data:
            title = page.title()
            
            if state.is_seen(title):
                logger.info(f"⏭️  Déjà vue: {title}")
                continue
            
            success, actions = processor.process(page, creator)
            
            if actions:
                state.mark_seen(title)
        
        # Sauvegardes
        state.save()
        
        duration = int(time.time() - start_time)
        if not DRY_RUN:
            components["wiki_logger"].save_to_wiki(BOT_NAME, duration, start_datetime)
        
        # Fermeture
        components["ia"].close()
        
        # Stats
        stats = processor.get_stats()
        logger.info("=" * 70)
        logger.info("📊 STATISTIQUES FINALES V4")
        logger.info("=" * 70)
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        logger.info(f"  Durée: {duration}s")
        logger.info("=" * 70)
        
        return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("⏹️  Interruption")
        sys.exit(130)
    except Exception as e:
        logger.error(f"💥 Erreur fatale: {e}", exc_info=True)
        sys.exit(1)