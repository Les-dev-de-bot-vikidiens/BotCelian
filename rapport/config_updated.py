#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Configuration complète du bot Vikidia avec nouvelles briques
"""

import os

# ================= API KEYS =================
MISTRAL_API_KEY = os.getenv("MISTRAL_API_KEY", "b2QebZ4uGFkxivnvgYQKHAG7eELuAcVj")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK", "https://discord.com/api/webhooks/1454143606578479306/8d--tJX5hidaFrMc4x4qI6I4pHD8l_hfGFYVXadh1q1fFlEExNATnXmcvEDzyH_nmvGw")

# ================= BOT INFO =================
BOT_NAME = "BotCélian"

# ================= SEUILS =================
MIN_WORDS_STUB = 200  # Nombre minimum de mots pour ne pas être une ébauche

# ================= NOTIFICATIONS =================
# Mentions Discord pour les alertes SI (format: "<@USER_ID> <@USER_ID>")
SI_USER_MENTIONS = "<@1368627541665124484> <@1397843398953664523>"

# ================= TIMEOUTS =================
DISCORD_TIMEOUT = 10  # Secondes
API_TIMEOUT = 30  # Secondes

# ================= RATE LIMITING =================
IA_MIN_INTERVAL = 2  # Secondes entre chaque appel IA
EDIT_MIN_INTERVAL = 1  # Secondes entre chaque édition wiki

# ================= RECHERCHE PAGES =================
RC_LOOKBACK_MINUTES = 15  # Minutes dans le passé pour chercher nouvelles pages
RC_LIMIT = 30  # Nombre maximum de pages à récupérer

# ================= IA SETTINGS =================
MISTRAL_MODEL = "mistral-small-latest"
MISTRAL_MAX_RETRIES = 3  # Tentatives max en cas d'erreur
MISTRAL_TEMPERATURE = 0.2  # Température pour l'analyse

# ================= LOGS =================
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
LOG_PAGE_YEAR = "2025"  # Année pour la page de logs
LOG_DIR = "logs"  # Répertoire des logs

# ================= LOGS STRUCTURÉS =================
STRUCTURED_LOGS_ENABLED = True  # Activer logs JSON
STRUCTURED_LOGS_DIR = "logs"  # Répertoire logs structurés

# ================= ALERTING =================
ALERTING_ENABLED = True  # Activer système d'alertes

# Ntfy (recommandé)
NTFY_TOPIC = os.getenv("NTFY_TOPIC", "botcelian-alerts")
NTFY_SERVER = "https://ntfy.sh"

# Pushover (optionnel)
PUSHOVER_TOKEN = os.getenv("PUSHOVER_TOKEN", "")
PUSHOVER_USER = os.getenv("PUSHOVER_USER", "")

# Seuils d'alerte
ALERT_EXECUTION_TIME_THRESHOLD = 600  # Secondes (10 minutes)
ALERT_ON_API_ERROR_AFTER = 3  # Alerter après N erreurs API consécutives

# ================= NOTIFICATIONS SI =================
SI_NOTIFICATIONS_ENABLED = True  # Activer notifications SI dédiées
SI_NTFY_TOPIC = os.getenv("SI_NTFY_TOPIC", "botcelian-si")
SI_COOLDOWN_DURATION = 300  # Secondes (5 minutes) entre notifications pour même page

# ================= AVERTO (DÉTECTION COPIE) =================
AVERTO_ENABLED = True  # Activer module Averto
AVERTO_SIMILARITY_THRESHOLD = 0.7  # Seuil de similarité pour copie (0-1)
AVERTO_MIN_TEXT_LENGTH = 100  # Longueur minimale pour vérifier
AVERTO_CHECK_WIKIPEDIA = True  # Vérifier Wikipedia
AVERTO_CHECK_WIKIMINI = True  # Vérifier Wikimini
AVERTO_AUTO_SI_THRESHOLD = 0.9  # SI automatique si similarité >= seuil

# ================= TERMES SENSIBLES =================
SENSITIVE_TERMS_ENABLED = True  # Activer détection termes sensibles
SENSITIVE_TERMS_CONFIG = "sensitive_terms.json"  # Fichier de configuration
SENSITIVE_TERMS_SI_THRESHOLD = 4  # Gravité minimale pour SI automatique (1-5)

# ================= SÉCURITÉ =================
MAX_EDITS_PER_RUN = 50  # Maximum d'éditions par exécution (sécurité)
ENABLE_SI_AUTO = True  # Permettre SI automatiques
ENABLE_TYPO_AUTO = True  # Permettre corrections typo automatiques
ENABLE_MAINTENANCE_AUTO = True  # Permettre ajout maintenance automatique

# Safety: toujours laisser à True pour éviter actions dangereuses
DRY_RUN = False  # Si True, aucune modification réelle n'est faite

# ================= WIKI =================
WIKI_BASE_URL = "https://fr.vikidia.org"
USER_AGENT = "BotCelian (https://fr.vikidia.org/wiki/Utilisateur:BotCélian)"

# ================= FEATURES FLAGS =================
FEATURES = {
    "structured_logging": STRUCTURED_LOGS_ENABLED,
    "alerting": ALERTING_ENABLED,
    "si_notifications": SI_NOTIFICATIONS_ENABLED,
    "averto": AVERTO_ENABLED,
    "sensitive_terms": SENSITIVE_TERMS_ENABLED,
    "typo_fixes": ENABLE_TYPO_AUTO,
    "maintenance": ENABLE_MAINTENANCE_AUTO,
    "auto_si": ENABLE_SI_AUTO
}

# ================= VALIDATION =================
def validate_config():
    """Valide la configuration"""
    errors = []
    warnings = []
    
    # Clés API
    if MISTRAL_API_KEY == "MISTRAL_API_KEY":
        errors.append("MISTRAL_API_KEY n'est pas configurée")
    
    if DISCORD_WEBHOOK.startswith("https://discord.com/api/webhooks/..."):
        warnings.append("DISCORD_WEBHOOK n'est pas configurée (notifications Discord désactivées)")
    
    # Seuils
    if MIN_WORDS_STUB < 10:
        errors.append("MIN_WORDS_STUB trop bas (minimum 10)")
    
    if AVERTO_SIMILARITY_THRESHOLD < 0 or AVERTO_SIMILARITY_THRESHOLD > 1:
        errors.append("AVERTO_SIMILARITY_THRESHOLD doit être entre 0 et 1")
    
    if SENSITIVE_TERMS_SI_THRESHOLD < 1 or SENSITIVE_TERMS_SI_THRESHOLD > 5:
        errors.append("SENSITIVE_TERMS_SI_THRESHOLD doit être entre 1 et 5")
    
    # Alerting
    if ALERTING_ENABLED and not NTFY_TOPIC:
        warnings.append("ALERTING_ENABLED=True mais NTFY_TOPIC non configuré")
    
    # SI Notifications
    if SI_NOTIFICATIONS_ENABLED and not (DISCORD_WEBHOOK or SI_NTFY_TOPIC):
        warnings.append("SI_NOTIFICATIONS_ENABLED=True mais aucun canal configuré")
    
    # Dry run
    if DRY_RUN:
        warnings.append("⚠️ MODE DRY_RUN ACTIVÉ - Aucune modification ne sera faite")
    
    # Afficher résultats
    if errors:
        raise ValueError("❌ Erreurs de configuration:\n  - " + "\n  - ".join(errors))
    
    if warnings:
        print("⚠️  Avertissements de configuration:")
        for warning in warnings:
            print(f"  - {warning}")
    
    print(f"✅ Configuration valide")
    print(f"   Features actives: {sum(FEATURES.values())}/{len(FEATURES)}")
    
    return True


def get_feature_status():
    """Retourne le statut des features"""
    return {
        name: "✅ Activé" if enabled else "❌ Désactivé"
        for name, enabled in FEATURES.items()
    }


if __name__ == "__main__":
    # Test de la configuration
    try:
        validate_config()
        
        print("\n📊 STATUT DES FEATURES:")
        for name, status in get_feature_status().items():
            print(f"  • {name}: {status}")
            
    except ValueError as e:
        print(f"❌ {e}")