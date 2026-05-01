"""
Handler para compra de contas de Streaming.
Fluxo: menu streaming → escolhe serviço → escolhe pagamento (saldo ou PIX) → entrega credenciais.
"""
import asyncio
import json
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import database
import payment
import webhook

logger = logging.getLogger(__name__)


# ─── Menu principal de streaming ─────────────────────────────────────────────

async def streaming_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe os serviços de streaming disponíveis."""
    query = update.callback_query
    await query.answer()

    servicos = await database.list_servicos_streaming()

    disponiveis = [s for s in servicos if s["disponivel"] > 0]

    if not disponiveis:
        await query.edit_message_text(
            "😔 <b>Streaming</b>\n\nNenhuma conta disponível no momento.\nVolte em breve!",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")
            ]]),
        )
        return

    # Busca texto customizado do banco; usa padrão como fallback
    mensagem = await database.get_setting("texto_streaming") or "🎬 <b>STREAMING & CONTEÚDO</b>\n\nEscolha o serviço desejado:\n\n"

    keyboard = []
    for s in disponiveis:
        texto = f"{s['servico']} — R$ {s['preco_brl']:.2f}  ({s['disponivel']} disponíveis)"
        keyboard.append([InlineKeyboardButton(texto, callback_data=f"stream_comprar_{s['servico']}")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")])

    await query.edit_message_text(
        mensagem,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ─── Escolha do serviço → formas de pagamento ────────────────────────────────

async def stream_comprar_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra opções de pagamento para o serviço escolhido."""
    query = update.callback_query
    await query.answer()

    servico = query.data.replace("stream_comprar_", "", 1)
    user = query.from_user

    preco = await database.get_preco_streaming(servico)
    if preco is None:
        await query.edit_message_text(
            f"😔 <b>{servico}</b> está sem estoque no momento.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_streaming")
            ]]),
        )
        return

    saldo = await database.get_user_balance(user.id)
    tem_saldo = saldo >= preco

    mensagem = (
        f"🎬 <b>{servico}</b>\n"
        f"💰 Preço: R$ {preco:.2f}\n"
        f"👛 Seu saldo: R$ {saldo:.2f}\n\n"
        f"Como deseja pagar?"
    )

    keyboard = []
    if tem_saldo:
        keyboard.append([
            InlineKeyboardButton(
                f"👛 Pagar com Saldo (R$ {saldo:.2f})",
                callback_data=f"stream_saldo_{servico}",
            )
        ])
    keyboard.append([
        InlineKeyboardButton("💳 Pagar com PIX", callback_data=f"stream_pix_{servico}")
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Voltar", callback_data="menu_streaming")
    ])

    await query.edit_message_text(
        mensagem,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ─── Entrega das credenciais ─────────────────────────────────────────────────

async def _entregar_streaming(bot, telegram_id: int, servico: str, preco: float, conta_id: int,
                               email: str, senha: str):
    """Envia as credenciais ao cliente no formato padrão."""
    await database.set_comprador_streaming(conta_id, telegram_id)

    mensagem = (
        f"✅ <b>Sua conta chegou!</b>\n\n"
        f"🎬 <b>{servico}</b>\n"
        f"💰 R$ {preco:.2f}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📧 Email: <tg-spoiler>{email}</tg-spoiler>\n"
        f"🔑 Senha: <tg-spoiler>{senha}</tg-spoiler>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👆 Toque para revelar as credenciais\n\n"
        f"⚠️ NÃO altere a senha!\n"
        f"⚠️ NÃO compartilhe estas credenciais!\n\n"
        f"Obrigado pela compra! 🎉"
    )
    await bot.send_message(chat_id=telegram_id, text=mensagem, parse_mode="HTML")


# ─── Pagamento via SALDO ─────────────────────────────────────────────────────

async def stream_saldo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa compra de streaming via saldo."""
    query = update.callback_query
    await query.answer()

    servico = query.data.replace("stream_saldo_", "", 1)
    user = query.from_user

    preco = await database.get_preco_streaming(servico)
    if preco is None:
        await query.edit_message_text(
            f"😔 <b>{servico}</b> ficou sem estoque agora.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_streaming")
            ]]),
        )
        return

    # Verifica saldo
    saldo = await database.get_user_balance(user.id)
    if saldo < preco:
        await query.edit_message_text(
            f"❌ <b>Saldo insuficiente.</b>\n\n"
            f"💰 Preço: R$ {preco:.2f}\n"
            f"👛 Seu saldo: R$ {saldo:.2f}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Pagar com PIX", callback_data=f"stream_pix_{servico}")],
                [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_streaming")],
            ]),
        )
        return

    await query.edit_message_text(
        f"⏳ Processando pagamento para <b>{servico}</b>...",
        parse_mode="HTML",
    )

    try:
        # Reserva a conta (FIFO)
        conta = await database.get_next_conta_streaming(servico)
        if not conta:
            await query.edit_message_text(
                f"😔 <b>{servico}</b> ficou sem estoque agora. Saldo não debitado.",
                parse_mode="HTML",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Voltar", callback_data="menu_streaming")
                ]]),
            )
            return

        # Debita saldo
        novo_saldo = await database.remove_user_balance(user.id, preco)

        # Entrega as credenciais
        await _entregar_streaming(
            context.bot, user.id, servico, preco,
            conta["id"], conta["email"], conta["senha"]
        )

        # 🔔 Postar notificação no canal de referência
        transaction_canal = {
            "plan_name":               servico,
            "data_gb":                 "",
            "amount_brl":              preco,
            "provider_transaction_id": f"saldo_stream_{user.id}_{servico}",
            "provider_payload":        {"streaming_servico": servico},
            "telegram_id":             user.id,
        }
        await webhook.postar_venda_no_canal(context.bot, transaction_canal, "streaming")

        await query.edit_message_text(
            f"✅ Pagamento com saldo processado!\n\n"
            f"🎬 Serviço: {servico}\n"
            f"💸 Valor: R$ {preco:.2f}\n"
            f"👛 Saldo restante: R$ {novo_saldo:.2f}\n\n"
            f"As credenciais foram enviadas acima! 👆",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")
            ]]),
        )

    except ValueError as e:
        await query.edit_message_text(
            f"❌ {e}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_streaming")
            ]]),
        )
    except Exception as e:
        logger.error(f"Erro na compra streaming via saldo: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Erro ao processar. Tente novamente.\n\nDetalhes: {e}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_streaming")
            ]]),
        )


# ─── Pagamento via PIX ───────────────────────────────────────────────────────

async def stream_pix_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera PIX para compra de streaming."""
    query = update.callback_query
    await query.answer()

    servico = query.data.replace("stream_pix_", "", 1)
    user = query.from_user

    preco = await database.get_preco_streaming(servico)
    if preco is None:
        await query.edit_message_text(
            f"😔 <b>{servico}</b> está sem estoque no momento.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_streaming")
            ]]),
        )
        return

    await query.edit_message_text(
        f"⏳ Gerando PIX para <b>{servico}</b>...\n\nAguarde um momento.",
        parse_mode="HTML",
    )

    try:
        charge_data = await payment.create_pix_charge(
            amount_brl=preco,
            description=f"Streaming {servico}",
            external_reference=f"stream_{servico}_user_{user.id}",
            customer_data={
                "telegram_id": user.id,
                "username":    user.username,
                "first_name":  user.first_name,
            },
        )

        # Salva no contexto para usar no webhook de confirmação
        # (o webhook vai usar o external_reference para saber que é streaming)
        await database.create_transaction(
            telegram_id=user.id,
            plan_id=0,
            amount_brl=preco,
            provider_transaction_id=charge_data["transaction_id"],
            qr_code=charge_data["qr_code"],
            copy_paste_code=charge_data["copy_paste_code"],
            provider_payload={**charge_data["raw_response"], "streaming_servico": servico},
        )

        mensagem = (
            f"✅ <b>PIX Gerado!</b>\n\n"
            f"🎬 Serviço: {servico}\n"
            f"💰 Valor: R$ {preco:.2f}\n\n"
            f"🔑 ID: <code>{charge_data['transaction_id']}</code>\n\n"
        )
        if charge_data["copy_paste_code"]:
            mensagem += (
                f"📋 <b>PIX Copia e Cola:</b>\n"
                f"<code>{charge_data['copy_paste_code']}</code>\n\n"
                f"Cole no seu app de banco para pagar.\n\n"
            )
        mensagem += "⏰ Após o pagamento, as credenciais serão enviadas aqui automaticamente!"

        keyboard = [
            [InlineKeyboardButton("🔄 Verificar Pagamento",
                                  callback_data=f"stream_check_{charge_data['transaction_id']}_{servico}")],
            [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")],
        ]

        await query.edit_message_text(
            mensagem,
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

        # Polling automático
        asyncio.create_task(
            _auto_check_stream(context.bot, user.id, charge_data["transaction_id"], servico, preco)
        )

    except Exception as e:
        logger.error(f"Erro ao criar PIX streaming: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Erro ao gerar PIX.\n\nDetalhes: {e}\n\nTente novamente.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_streaming")
            ]]),
        )


async def _auto_check_stream(bot, telegram_id: int, transaction_id: str, servico: str, preco: float):
    """Polling automático de confirmação do PIX de streaming."""
    for _ in range(60):
        await asyncio.sleep(5)
        try:
            status = await payment.check_transaction_status(transaction_id)
            if status == "paid":
                tx = await database.get_transaction_by_provider_id(transaction_id)
                if tx and tx["status"] != "delivered":
                    await database.mark_transaction_paid(transaction_id)
                    conta = await database.get_next_conta_streaming(servico)
                    if conta:
                        await _entregar_streaming(
                            bot, telegram_id, servico, preco,
                            conta["id"], conta["email"], conta["senha"]
                        )
                        await database.mark_transaction_delivered(transaction_id, delivery_payload="{}")
                    else:
                        await bot.send_message(
                            chat_id=telegram_id,
                            text=(
                                f"✅ Pagamento confirmado!\n\n"
                                f"😔 Infelizmente o estoque de <b>{servico}</b> acabou.\n"
                                f"Nossa equipe entrará em contato em breve para providenciar sua conta."
                            ),
                            parse_mode="HTML",
                        )
                return
            elif status in ("canceled", "expired", "failed"):
                await database.update_transaction_status(transaction_id, "failed")
                return
        except Exception as e:
            logger.error(f"Erro ao verificar PIX streaming: {e}")


async def stream_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verificação manual do PIX de streaming."""
    query = update.callback_query
    await query.answer("Verificando pagamento...")

    partes = query.data.split("_", 3)
    # formato: stream_check_{transaction_id}_{servico}
    transaction_id = partes[2]
    servico = partes[3] if len(partes) > 3 else ""

    transaction = await database.get_transaction_by_provider_id(transaction_id)
    if not transaction:
        await query.answer("❌ Transação não encontrada.", show_alert=True)
        return

    api_status = await payment.check_transaction_status(transaction_id)

    if api_status == "paid" and transaction["status"] == "pending":
        await database.mark_transaction_paid(transaction_id)
        conta = await database.get_next_conta_streaming(servico)
        if conta:
            await _entregar_streaming(
                context.bot, query.from_user.id, servico,
                transaction["amount_brl"], conta["id"], conta["email"], conta["senha"]
            )
            await database.mark_transaction_delivered(transaction_id, delivery_payload="{}")
            await query.edit_message_text(
                f"✅ Pagamento confirmado! Credenciais enviadas acima! 👆",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")
                ]]),
            )
        else:
            await query.edit_message_text(
                f"✅ Pagamento confirmado!\n😔 Estoque esgotado — nossa equipe entrará em contato.",
                reply_markup=InlineKeyboardMarkup([[
                    InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")
                ]]),
            )
        return

    status_map = {
        "pending":   "⏳ Ainda não confirmado. Aguarde e tente novamente.",
        "paid":      "✅ Pagamento já confirmado!",
        "delivered": "🎉 Conta já entregue!",
        "failed":    "❌ Pagamento falhou ou foi cancelado.",
    }
    msg = status_map.get(transaction["status"], "❓ Status desconhecido.")

    await query.edit_message_text(
        f"🔍 <b>Status</b>\n\n🎬 {servico}\n💰 R$ {transaction['amount_brl']:.2f}\n\n{msg}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Verificar Novamente",
                                  callback_data=f"stream_check_{transaction_id}_{servico}")],
            [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")],
        ]),
    )


# ─── Registro dos handlers ───────────────────────────────────────────────────

def register_handlers(application):
    application.add_handler(CallbackQueryHandler(streaming_menu_callback, pattern="^menu_streaming$"))
    application.add_handler(CallbackQueryHandler(stream_comprar_callback, pattern="^stream_comprar_"))
    application.add_handler(CallbackQueryHandler(stream_saldo_callback,   pattern="^stream_saldo_"))
    application.add_handler(CallbackQueryHandler(stream_pix_callback,     pattern="^stream_pix_"))
    application.add_handler(CallbackQueryHandler(stream_check_callback,   pattern="^stream_check_"))
