"""
Integração com PushinPay para cobrança PIX.
Docs: https://app.theneo.io/pushinpay/pix/criar-pix

O token da Pusshipay é carregado dinamicamente do banco de dados a cada chamada,
permitindo que o admin altere o token pelo painel sem reiniciar o bot.
"""
import aiohttp
from typing import Dict, Any, Optional
import config
import hmac
import hashlib
import database


async def _get_token() -> str:
    """
    Retorna o token da Pusshipay.
    Prioridade: banco de dados (admin pode alterar pelo painel) → config.py (fallback).
    """
    token = await database.get_pusshipay_token()
    if not token:
        raise Exception(
            "Token da Pusshipay não configurado. "
            "Acesse o painel admin → 🔑 Gateway → Alterar Token Pusshipay."
        )
    return token


async def create_pix_charge(amount_brl: float, description: str,
                            external_reference: str, customer_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Cria uma cobrança PIX via PushinPay.

    Args:
        amount_brl: Valor em reais (será convertido para centavos)
        description: Descrição da cobrança
        external_reference: Referência externa (ex: plan_id + user_id)
        customer_data: Dados opcionais do cliente

    Returns:
        Dict com transaction_id, qr_code, copy_paste_code

    Raises:
        Exception: Se a requisição falhar
    """
    token = await _get_token()

    url = f"{config.PUSHSHIPAY_BASE_URL}/pix/cashIn"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }

    # PushinPay usa valor em CENTAVOS (mínimo 50)
    value_cents = int(round(amount_brl * 100))

    payload = {
        "value": value_cents,
    }

    # Adicionar webhook URL se configurado
    if config.WEBHOOK_PUBLIC_URL:
        payload["webhook_url"] = config.WEBHOOK_PUBLIC_URL

    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as response:
            if response.status not in (200, 201):
                error_text = await response.text()
                raise Exception(f"Erro ao criar cobrança PIX: {response.status} - {error_text}")

            data = await response.json()
            return parse_charge_response(data)


async def check_transaction_status(transaction_id: str) -> str:
    """
    Consulta o status de uma transação na PushinPay.
    GET /transaction/{id}

    Returns:
        Status: 'created', 'paid', 'canceled'
    """
    token = await _get_token()

    url = f"{config.PUSHSHIPAY_BASE_URL}/transaction/{transaction_id}"

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=headers) as response:
            if response.status != 200:
                return "unknown"
            data = await response.json()
            return data.get("status", "unknown")


def parse_charge_response(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza a resposta da PushinPay.
    Resposta esperada: id, qr_code, status, value, qr_code_base64
    """
    transaction_id = data.get("id")

    # qr_code é o código copia-e-cola (EMV)
    qr_code = data.get("qr_code") or ""

    # qr_code_base64 é a imagem do QR code
    qr_code_base64 = data.get("qr_code_base64") or ""

    if not transaction_id:
        raise ValueError("Resposta da API não contém ID da transação")

    return {
        "transaction_id": str(transaction_id),
        "qr_code": qr_code_base64,
        "copy_paste_code": qr_code,
        "raw_response": data
    }


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    """
    Verifica a assinatura do webhook (se configurado).
    """
    if not config.PUSHSHIPAY_WEBHOOK_SECRET:
        return True

    expected_signature = hmac.new(
        config.PUSHSHIPAY_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature)


def normalize_webhook_payload(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normaliza o payload do webhook da PushinPay.
    Webhook envia: transaction_id/id e status (paid)
    """
    transaction_id = (
        data.get("transaction_id") or
        data.get("id") or
        data.get("charge_id")
    )

    status = (
        data.get("status") or ""
    ).lower()

    # Normalizar status
    if status in ("paid", "approved", "confirmed", "completed"):
        status = "paid"
    elif status in ("pending", "waiting", "created"):
        status = "pending"
    elif status in ("failed", "cancelled", "canceled", "rejected", "expired"):
        status = "failed"

    return {
        "transaction_id": str(transaction_id) if transaction_id else None,
        "status": status,
        "raw_payload": data
    }
