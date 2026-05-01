"""
Configuração central do bot de venda de eSIM.
"""
import os

# Token do bot Telegram
BOT_TOKEN = os.getenv("BOT_TOKEN", "8023581550:AAEUeDIyE1I8jTBfq53Zg9uCx8A-NHBuClU")

# Configuração PushShipay
PUSHSHIPAY_BASE_URL = os.getenv("PUSHSHIPAY_BASE_URL", "https://api.pushinpay.com.br/api")
PUSHSHIPAY_API_TOKEN = os.getenv("PUSHSHIPAY_API_TOKEN", "64098|SySaA6zHrFUnD9gzJlA8YW6i31FtXjkQL5zl39mKda68f392")
PUSHSHIPAY_WEBHOOK_SECRET = os.getenv("PUSHSHIPAY_WEBHOOK_SECRET", "")

# Configuração do webhook
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "8443"))
WEBHOOK_PATH = os.getenv("WEBHOOK_PATH", "/webhook/payment")
WEBHOOK_PUBLIC_URL = os.getenv("WEBHOOK_PUBLIC_URL", "https://e901-170-245-95-178.ngrok-free.app/webhook/payment")

# Banco de dados
DATABASE_PATH = os.getenv("DATABASE_PATH", "esim_bot.db")

# IDs dos administradores
ADMIN_IDS_STR = os.getenv("ADMIN_IDS", "8733953122")


def get_admin_ids() -> set[int]:
    """Retorna conjunto de IDs de administradores."""
    if not ADMIN_IDS_STR:
        return set()
    try:
        return {int(id_str.strip()) for id_str in ADMIN_IDS_STR.split(",") if id_str.strip()}
    except ValueError:
        return set()


def validate_config():
    """Valida se as configurações críticas estão presentes."""
    errors = []
    if BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
        errors.append("BOT_TOKEN não configurado")
    if PUSHSHIPAY_API_TOKEN == "YOUR_PUSHSHIPAY_TOKEN_HERE":
        errors.append("PUSHSHIPAY_API_TOKEN não configurado")
    if errors:
        raise ValueError(f"Configuração incompleta: {', '.join(errors)}")
