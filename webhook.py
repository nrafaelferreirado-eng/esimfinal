"""
Servidor webhook para confirmação de pagamento PIX via PushiPay.
Entrega automática da foto (eSIM) ou credenciais (streaming) ao cliente após pagamento confirmado.
Após cada venda confirmada, posta aviso no canal de referência configurado.
"""

from aiohttp import web
import logging
import json
import payment
import database

logger = logging.getLogger(__name__)


# ─── Postar venda no canal de referência ─────────────────────────────────────

async def postar_venda_no_canal(bot, transaction: dict, tipo: str):
    """
    Posta notificação de venda no canal de referência configurado.
    tipo: 'esim' ou 'streaming'
    """
    try:
        canal_id = await database.get_setting("canal_referencia_id")
        if not canal_id:
            return  # Canal não configurado, ignora silenciosamente

        # Converte para int se for número (ex: "-1001234567890")
        try:
            canal_id = int(canal_id)
        except (ValueError, TypeError):
            pass  # Mantém como string se for @username

        plan_name  = transaction.get("plan_name", "")
        data_gb    = transaction.get("data_gb", "")
        amount_brl = float(transaction.get("amount_brl", 0))

        if tipo == "esim":
            mensagem = (
                f"🟢 <b>VENDA REALIZADA!</b>\n\n"
                f"📱 <b>eSIM vendido</b>\n"
                f"📦 Plano: <b>{plan_name}</b>\n"
                f"📊 Dados: <b>{data_gb} GB</b>\n"
                f"💰 Valor: <b>R$ {amount_brl:.2f}</b>\n\n"
                f"✅ Entregue automaticamente ao cliente!"
            )
        else:
            provider_payload = transaction.get("provider_payload") or {}
            if isinstance(provider_payload, str):
                try:
                    provider_payload = json.loads(provider_payload)
                except Exception:
                    provider_payload = {}
            servico = provider_payload.get("streaming_servico", "Streaming")
            mensagem = (
                f"🟢 <b>VENDA REALIZADA!</b>\n\n"
                f"🎬 <b>Streaming vendido</b>\n"
                f"📺 Serviço: <b>{servico}</b>\n"
                f"💰 Valor: <b>R$ {amount_brl:.2f}</b>\n\n"
                f"✅ Credenciais entregues automaticamente ao cliente!"
            )

        await bot.send_message(
            chat_id=canal_id,
            text=mensagem,
            parse_mode="HTML",
        )
        logger.info(f"✅ Venda postada no canal {canal_id}")

    except Exception as e:
        logger.error(f"❌ ERRO ao postar no canal: {type(e).__name__}: {e}", exc_info=True)


# ─── Entrega de streaming via PIX ────────────────────────────────────────────

async def deliver_streaming_for_transaction(transaction: dict, bot) -> dict:
    """
    Entrega credenciais de streaming após pagamento PIX confirmado.
    Retorna dict com status: 'delivered', 'estoque_vazio' ou 'error'.
    """
    telegram_id = transaction["telegram_id"]
    amount_brl  = transaction.get("amount_brl", 0)

    provider_payload = transaction.get("provider_payload") or {}
    if isinstance(provider_payload, str):
        try:
            provider_payload = json.loads(provider_payload)
        except Exception:
            provider_payload = {}

    servico = provider_payload.get("streaming_servico", "Streaming")

    conta = await database.get_next_conta_streaming(servico)

    if not conta:
        logger.warning(f"⚠️ Estoque de streaming vazio para serviço: {servico}")

        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"✅ <b>Pagamento confirmado!</b>\n\n"
                    f"🎬 Serviço: <b>{servico}</b>\n"
                    f"💰 Valor: R$ {float(amount_brl):.2f}\n\n"
                    f"⏳ Estamos repondo o estoque deste serviço.\n"
                    f"Você receberá suas credenciais em breve. Pedimos desculpas!"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Erro ao notificar cliente sobre estoque vazio de streaming: {e}")

        await _alertar_admins_estoque_vazio(bot, servico, transaction)
        return {"status": "estoque_vazio", "servico": servico}

    try:
        await database.set_comprador_streaming(conta["id"], telegram_id)

        mensagem = (
            f"✅ <b>Pagamento confirmado! Sua conta chegou!</b>\n\n"
            f"🎬 <b>{servico}</b>\n"
            f"💰 R$ {float(amount_brl):.2f}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n"
            f"📧 Email: <tg-spoiler>{conta['email']}</tg-spoiler>\n"
            f"🔑 Senha: <tg-spoiler>{conta['senha']}</tg-spoiler>\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"👆 Toque para revelar as credenciais\n\n"
            f"⚠️ NÃO altere a senha!\n"
            f"⚠️ NÃO compartilhe estas credenciais!\n\n"
            f"Obrigado pela compra! 🎉"
        )
        await bot.send_message(chat_id=telegram_id, text=mensagem, parse_mode="HTML")
        logger.info(f"✅ Streaming entregue: {servico} → user {telegram_id}")
        return {"status": "delivered", "servico": servico, "conta_id": conta["id"]}

    except Exception as e:
        logger.error(f"Erro ao entregar credenciais de streaming: {e}", exc_info=True)
        await _alertar_admins_erro(bot, servico, transaction, str(e))
        return {"status": "error", "message": str(e)}


# ─── Entrega da foto (eSIM) ──────────────────────────────────────────────────

async def deliver_foto_for_transaction(transaction: dict, bot) -> dict:
    """
    Busca a próxima foto do estoque e entrega ao cliente via Telegram.
    Retorna dict com status: 'delivered', 'estoque_vazio' ou 'error'.
    """
    plan_id     = transaction["plan_id"]
    plan_name   = transaction.get("plan_name", "")
    telegram_id = transaction["telegram_id"]
    data_gb     = transaction.get("data_gb", "")
    amount_brl  = transaction.get("amount_brl", 0)

    foto_file_id = await database.get_next_estoque_foto(plan_id)

    if not foto_file_id:
        logger.warning(f"⚠️ Estoque vazio para plano {plan_id} ({plan_name})")

        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=(
                    f"✅ <b>Pagamento confirmado!</b>\n\n"
                    f"📦 Plano: <b>{plan_name}</b>\n"
                    f"💰 Valor: R$ {float(amount_brl):.2f}\n\n"
                    f"⏳ Estamos repondo o estoque deste plano.\n"
                    f"Você receberá seu acesso em breve. Pedimos desculpas!"
                ),
                parse_mode="HTML",
            )
        except Exception as e:
            logger.error(f"Erro ao notificar cliente sobre estoque vazio: {e}")

        await _alertar_admins_estoque_vazio(bot, plan_name, transaction)
        return {"status": "estoque_vazio", "plan_id": plan_id}

    try:
        await bot.send_photo(
            chat_id=telegram_id,
            photo=foto_file_id,
            caption=(
                f"✅ <b>Pagamento confirmado!</b>\n\n"
                f"📦 Plano: <b>{plan_name}</b>\n"
                f"📊 Dados: {data_gb} GB\n"
                f"💰 Valor: R$ {float(amount_brl):.2f}\n\n"
                f"📎 Seu arquivo de acesso está anexado acima.\n"
                f"Qualquer dúvida, fale com o suporte. 🚀"
            ),
            parse_mode="HTML",
        )
        logger.info(f"✅ Foto entregue: plano {plan_id} → user {telegram_id}")
        return {"status": "delivered", "foto_file_id": foto_file_id}

    except Exception as e:
        logger.error(f"Erro ao entregar foto: {e}", exc_info=True)
        await _alertar_admins_erro(bot, plan_name, transaction, str(e))
        return {"status": "error", "message": str(e)}


# ─── Alertas para admins ─────────────────────────────────────────────────────

async def _alertar_admins_estoque_vazio(bot, nome: str, transaction: dict):
    try:
        admins = await database.list_admins()
        for admin in admins:
            try:
                await bot.send_message(
                    chat_id=admin["telegram_id"],
                    text=(
                        f"⚠️ <b>ESTOQUE VAZIO — AÇÃO NECESSÁRIA</b>\n\n"
                        f"📦 Produto: <b>{nome}</b>\n"
                        f"🆔 Transação: <code>{transaction.get('provider_transaction_id', '')}</code>\n"
                        f"👤 Cliente aguardando: <code>{transaction['telegram_id']}</code>\n\n"
                        f"Acesse /admin para adicionar mais itens ao estoque."
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Não foi possível alertar admin {admin['telegram_id']}: {e}")
    except Exception as e:
        logger.error(f"Erro ao listar admins para alerta: {e}")


async def _alertar_admins_erro(bot, nome: str, transaction: dict, erro: str):
    try:
        admins = await database.list_admins()
        for admin in admins:
            try:
                await bot.send_message(
                    chat_id=admin["telegram_id"],
                    text=(
                        f"🚨 <b>ERRO NA ENTREGA</b>\n\n"
                        f"📦 Produto: {nome}\n"
                        f"🆔 Transação: <code>{transaction.get('provider_transaction_id', '')}</code>\n"
                        f"👤 Cliente: <code>{transaction['telegram_id']}</code>\n"
                        f"❌ Erro: {erro}"
                    ),
                    parse_mode="HTML",
                )
            except Exception as e:
                logger.warning(f"Não foi possível alertar admin {admin['telegram_id']}: {e}")
    except Exception as e:
        logger.error(f"Erro ao listar admins para alerta de erro: {e}")


# ─── Handler principal do webhook ────────────────────────────────────────────

async def handle_webhook(request):
    """Handler principal do webhook de pagamento PushiPay."""
    try:
        body = await request.read()
        logger.info(f"Webhook raw body: {body.decode('utf-8', errors='replace')}")

        signature = request.headers.get("X-Signature", "")
        if not payment.verify_webhook_signature(body, signature):
            logger.warning("Webhook com assinatura inválida")
            return web.json_response({"error": "Invalid signature"}, status=401)

        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            try:
                from urllib.parse import parse_qs
                parsed = parse_qs(body.decode())
                data = {k: v[0] if len(v) == 1 else v for k, v in parsed.items()}
            except Exception:
                logger.error("Webhook com payload inválido")
                return web.json_response({"error": "Invalid payload"}, status=400)

        logger.info(f"Webhook parsed data: {data}")

        normalized     = payment.normalize_webhook_payload(data)
        transaction_id = normalized.get("transaction_id")
        status         = normalized.get("status") or "paid"

        if not transaction_id:
            logger.error("Webhook sem transaction_id")
            return web.json_response({"error": "Missing transaction_id"}, status=400)

        logger.info(f"Webhook: transaction_id={transaction_id}, status={status}")

        transaction = await database.get_transaction_by_provider_id(transaction_id)
        if not transaction:
            logger.warning(f"Transação não encontrada: {transaction_id}")
            return web.json_response({"error": "Transaction not found"}, status=404)

        if status == "paid" and transaction["status"] not in ("paid", "delivered"):
            await database.mark_transaction_paid(transaction_id)

            bot = request.app["bot"]

            provider_payload = transaction.get("provider_payload") or {}
            if isinstance(provider_payload, str):
                try:
                    provider_payload = json.loads(provider_payload)
                except Exception:
                    provider_payload = {}

            is_streaming = bool(provider_payload.get("streaming_servico"))

            if is_streaming:
                delivery_result = await deliver_streaming_for_transaction(transaction, bot)
            else:
                delivery_result = await deliver_foto_for_transaction(transaction, bot)

            if delivery_result.get("status") == "delivered":
                await database.mark_transaction_delivered(
                    transaction_id,
                    delivery_payload=json.dumps(delivery_result),
                )
                logger.info(f"✅ Transação {transaction_id} entregue com sucesso")

                # ✅ Postar venda no canal de referência
                tipo = "streaming" if is_streaming else "esim"
                await postar_venda_no_canal(bot, transaction, tipo)

        elif transaction["status"] == "delivered":
            logger.info(f"Transação {transaction_id} já entregue. Ignorando.")

        return web.json_response({"status": "ok", "received": True})

    except Exception as e:
        logger.error(f"Erro ao processar webhook: {e}", exc_info=True)
        return web.json_response({"error": "Internal error"}, status=500)


# ─── App aiohttp ─────────────────────────────────────────────────────────────

def create_webhook_app(bot) -> web.Application:
    app = web.Application()
    app["bot"] = bot
    return app


async def start_webhook_server(app, host: str, port: int):
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    logger.info(f"Webhook server rodando em {host}:{port}")
    return runner
