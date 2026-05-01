"""
Handler para compra de eSIM.
Suporta pagamento via PIX (PushinPay) e via Saldo da carteira.
"""
import asyncio
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import database
import payment
import webhook
import logging

logger = logging.getLogger(__name__)


# ─── Lista de planos ─────────────────────────────────────────────────────────

async def buy_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra a lista de planos disponíveis."""
    query = update.callback_query
    await query.answer()

    plans = await database.list_plans(active_only=True)

    if not plans:
        keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")]]
        await query.edit_message_text(
            "😔 Desculpe, não há planos disponíveis no momento.\n\nTente novamente mais tarde.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
        return

    # Busca texto customizado do banco; usa padrão como fallback
    texto_buy = await database.get_setting("texto_comprar_esim") or "🛒 <b>Planos Disponíveis</b>\n\nEscolha um plano para comprar:\n\n"
    message = texto_buy

    keyboard = []
    for plan in plans:
        plan_text = f"{plan['name']} - {plan['data_gb']} GB - R$ {plan['price_brl']:.2f}"
        keyboard.append([InlineKeyboardButton(plan_text, callback_data=f"buy_plan_{plan['id']}")])

    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")])

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ─── Escolha do plano → mostrar formas de pagamento ─────────────────────────

async def buy_plan_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Após o cliente escolher o plano, verifica estoque, saldo e oferece as opções
    de pagamento disponíveis (Saldo e/ou PIX).
    """
    query = update.callback_query
    await query.answer()

    plan_id = int(query.data.split("_")[2])
    user = query.from_user

    plan = await database.get_plan(plan_id)
    if not plan or not plan["is_active"]:
        await query.edit_message_text(
            "❌ Plano não encontrado ou não está mais disponível.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_buy")
            ]]),
        )
        return

    # ✅ VERIFICA ESTOQUE ANTES DE MOSTRAR OPÇÕES DE PAGAMENTO
    estoque_info = await database.get_estoque(plan_id)
    disponivel = 0
    if estoque_info:
        disponivel = estoque_info[0].get("disponivel", 0)

    if disponivel <= 0:
        keyboard = [[InlineKeyboardButton("⬅️ Voltar aos Planos", callback_data="menu_buy")]]
        await query.edit_message_text(
            f"😔 <b>Estoque esgotado!</b>\n\n"
            f"O plano <b>{plan['name']}</b> está temporariamente sem estoque.\n\n"
            f"Por favor, tente novamente mais tarde ou escolha outro plano.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return

    # Busca saldo atual do cliente
    saldo = await database.get_user_balance(user.id)
    tem_saldo = saldo >= plan["price_brl"]

    message = (
        f"📦 <b>{plan['name']}</b>\n"
        f"📊 Dados: {plan['data_gb']} GB\n"
        f"💰 Preço: R$ {plan['price_brl']:.2f}\n"
        f"👛 Seu saldo: R$ {saldo:.2f}\n\n"
        f"Como deseja pagar?"
    )

    keyboard = []

    if tem_saldo:
        keyboard.append([
            InlineKeyboardButton(
                f"👛 Pagar com Saldo (R$ {saldo:.2f})",
                callback_data=f"pay_saldo_{plan_id}",
            )
        ])

    keyboard.append([
        InlineKeyboardButton("💳 Pagar com PIX", callback_data=f"pay_pix_{plan_id}")
    ])
    keyboard.append([
        InlineKeyboardButton("⬅️ Voltar", callback_data="menu_buy")
    ])

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ─── Pagamento via SALDO ─────────────────────────────────────────────────────

async def pay_saldo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Processa a compra debitando do saldo da carteira e entrega a foto do estoque."""
    query = update.callback_query
    await query.answer()

    plan_id = int(query.data.split("_")[2])
    user = query.from_user

    plan = await database.get_plan(plan_id)
    if not plan or not plan["is_active"]:
        await query.edit_message_text(
            "❌ Plano não disponível.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_buy")
            ]]),
        )
        return

    # ✅ VERIFICA ESTOQUE ANTES DE DEBITAR SALDO
    estoque_info = await database.get_estoque(plan_id)
    disponivel = 0
    if estoque_info:
        disponivel = estoque_info[0].get("disponivel", 0)

    if disponivel <= 0:
        keyboard = [[InlineKeyboardButton("⬅️ Voltar aos Planos", callback_data="menu_buy")]]
        await query.edit_message_text(
            f"😔 <b>Estoque esgotado!</b>\n\n"
            f"O plano <b>{plan['name']}</b> está temporariamente sem estoque.\n\n"
            f"Seu saldo <b>não foi debitado</b>.\n"
            f"Por favor, tente novamente mais tarde ou escolha outro plano.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return

    # Verifica saldo (segurança — evita race condition)
    saldo = await database.get_user_balance(user.id)
    if saldo < plan["price_brl"]:
        await query.edit_message_text(
            f"❌ <b>Saldo insuficiente.</b>\n\n"
            f"💰 Preço do plano: R$ {plan['price_brl']:.2f}\n"
            f"👛 Seu saldo: R$ {saldo:.2f}\n\n"
            f"Utilize o PIX para completar sua compra.",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💳 Pagar com PIX", callback_data=f"pay_pix_{plan_id}")],
                [InlineKeyboardButton("⬅️ Voltar", callback_data="menu_buy")],
            ]),
        )
        return

    await query.edit_message_text(
        f"⏳ Processando pagamento com saldo para <b>{plan['name']}</b>...",
        parse_mode="HTML",
    )

    try:
        # Debita o saldo
        novo_saldo = await database.remove_user_balance(user.id, plan["price_brl"])

        # Registra a transação como paga diretamente
        transaction_id = f"saldo_{user.id}_{plan_id}_{int(asyncio.get_event_loop().time())}"
        await database.create_transaction(
            telegram_id=user.id,
            plan_id=plan_id,
            amount_brl=plan["price_brl"],
            provider_transaction_id=transaction_id,
            qr_code="",
            copy_paste_code="",
            provider_payload={"method": "saldo", "telegram_id": user.id},
        )
        await database.mark_transaction_paid(transaction_id)

        # Monta o dict de transação no mesmo formato que o webhook usa
        transaction = {
            "plan_id":                  plan_id,
            "plan_name":                plan["name"],
            "telegram_id":              user.id,
            "data_gb":                  plan["data_gb"],
            "amount_brl":               plan["price_brl"],
            "provider_transaction_id":  transaction_id,
        }

        bot = context.bot

        # ✅ Entrega a foto do estoque — mesma lógica do webhook PIX
        delivery_result = await webhook.deliver_foto_for_transaction(transaction, bot)

        if delivery_result.get("status") == "delivered":
            await database.mark_transaction_delivered(
                transaction_id,
                delivery_payload=json.dumps(delivery_result),
            )
            logger.info(f"Compra via saldo entregue: user={user.id} plan={plan_id}")

            # 🔔 Postar notificação no canal de referência (igual ao fluxo PIX)
            await webhook.postar_venda_no_canal(bot, transaction, "esim")

            # Confirmação de saldo restante (a foto já foi enviada pela função acima)
            await bot.send_message(
                chat_id=user.id,
                text=(
                    f"👛 Saldo restante: R$ {novo_saldo:.2f}"
                ),
                parse_mode="HTML",
            )

        elif delivery_result.get("status") == "estoque_vazio":
            # Cliente já foi avisado dentro de deliver_foto_for_transaction
            # Só registra como pago (não entregue ainda)
            logger.warning(f"Saldo debitado mas estoque vazio: user={user.id} plan={plan_id}")
            await bot.send_message(
                chat_id=user.id,
                text=f"👛 Saldo restante: R$ {novo_saldo:.2f}",
            )

        else:
            # Erro na entrega — admins já foram alertados pelo webhook
            logger.error(f"Erro na entrega via saldo: {delivery_result}")

        # Edita a mensagem original para não ficar com "Processando..."
        await query.edit_message_text(
            f"✅ Pagamento com saldo processado!\n\n"
            f"📦 Plano: {plan['name']}\n"
            f"💸 Valor: R$ {plan['price_brl']:.2f}\n"
            f"👛 Saldo restante: R$ {novo_saldo:.2f}",
            parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")
            ]]),
        )

    except ValueError as e:
        await query.edit_message_text(
            f"❌ {e}",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_buy")
            ]]),
        )
    except Exception as e:
        logger.error(f"Erro no pagamento via saldo: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Erro ao processar pagamento.\n\nDetalhes: {str(e)}\n\nTente novamente.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_buy")
            ]]),
        )


# ─── Pagamento via PIX ───────────────────────────────────────────────────────

async def pay_pix_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera a cobrança PIX via PushinPay."""
    query = update.callback_query
    await query.answer()

    plan_id = int(query.data.split("_")[2])
    user = query.from_user

    plan = await database.get_plan(plan_id)
    if not plan or not plan["is_active"]:
        await query.edit_message_text(
            "❌ Plano não encontrado ou não está mais disponível.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_buy")
            ]]),
        )
        return

    # ✅ VERIFICA ESTOQUE ANTES DE GERAR PIX
    estoque_info = await database.get_estoque(plan_id)
    disponivel = 0
    if estoque_info:
        disponivel = estoque_info[0].get("disponivel", 0)

    if disponivel <= 0:
        keyboard = [[InlineKeyboardButton("⬅️ Voltar aos Planos", callback_data="menu_buy")]]
        await query.edit_message_text(
            f"😔 <b>Estoque esgotado!</b>\n\n"
            f"O plano <b>{plan['name']}</b> está temporariamente sem estoque.\n\n"
            f"Nenhuma cobrança foi gerada.\n"
            f"Por favor, tente novamente mais tarde ou escolha outro plano.",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )
        return

    await query.edit_message_text(
        f"⏳ Gerando cobrança PIX para o plano <b>{plan['name']}</b>...\n\nAguarde um momento.",
        parse_mode="HTML",
    )

    try:
        charge_data = await payment.create_pix_charge(
            amount_brl=plan["price_brl"],
            description=f"eSIM {plan['name']} - {plan['data_gb']} GB",
            external_reference=f"plan_{plan_id}_user_{user.id}",
            customer_data={
                "telegram_id": user.id,
                "username": user.username,
                "first_name": user.first_name,
            },
        )

        await database.create_transaction(
            telegram_id=user.id,
            plan_id=plan_id,
            amount_brl=plan["price_brl"],
            provider_transaction_id=charge_data["transaction_id"],
            qr_code=charge_data["qr_code"],
            copy_paste_code=charge_data["copy_paste_code"],
            provider_payload=charge_data["raw_response"],
        )

        message = (
            f"✅ <b>Cobrança PIX Gerada!</b>\n\n"
            f"📦 Plano: {plan['name']}\n"
            f"📊 Dados: {plan['data_gb']} GB\n"
            f"💰 Valor: R$ {plan['price_brl']:.2f}\n\n"
            f"🔑 ID da transação: <code>{charge_data['transaction_id']}</code>\n\n"
        )

        if charge_data["copy_paste_code"]:
            message += (
                f"📋 <b>PIX Copia e Cola:</b>\n"
                f"<code>{charge_data['copy_paste_code']}</code>\n\n"
                f"Clique para copiar o código acima e cole no seu app de pagamento.\n\n"
            )

        message += (
            "⏰ Após realizar o pagamento, você receberá uma confirmação "
            "automática aqui no chat.\n\n"
            "O eSIM será processado e entregue em seguida."
        )

        keyboard = [
            [InlineKeyboardButton(
                "🔄 Verificar Pagamento",
                callback_data=f"check_payment_{charge_data['transaction_id']}",
            )],
            [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")],
        ]

        await query.edit_message_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="HTML",
        )

        asyncio.create_task(
            auto_check_payment(context.bot, user.id, charge_data["transaction_id"], plan)
        )

    except Exception as e:
        logger.error(f"Erro ao criar cobrança PIX: {e}", exc_info=True)
        await query.edit_message_text(
            f"❌ Erro ao gerar cobrança PIX.\n\nDetalhes: {str(e)}\n\nTente novamente mais tarde.",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar", callback_data="menu_buy")
            ]]),
        )


# ─── Verificação automática de pagamento PIX ────────────────────────────────

async def auto_check_payment(bot, telegram_id: int, transaction_id: str, plan: dict):
    """Verifica automaticamente se o pagamento foi confirmado (polling)."""
    for _ in range(60):  # 60 tentativas x 5s = 5 minutos
        await asyncio.sleep(5)
        try:
            status = await payment.check_transaction_status(transaction_id)
            if status == "paid":
                await database.mark_transaction_paid(transaction_id)
                await bot.send_message(
                    chat_id=telegram_id,
                    text=(
                        f"✅ <b>Pagamento confirmado!</b>\n\n"
                        f"📦 Plano: {plan['name']}\n"
                        f"📊 Dados: {plan['data_gb']} GB\n"
                        f"💰 Valor: R$ {plan['price_brl']:.2f}\n\n"
                        f"⏳ Seu eSIM está sendo processado e será entregue em breve."
                    ),
                    parse_mode="HTML",
                )
                logger.info(f"Pagamento PIX confirmado: {transaction_id}")
                return
            elif status in ("canceled", "expired", "failed"):
                await database.update_transaction_status(transaction_id, "failed")
                return
        except Exception as e:
            logger.error(f"Erro ao verificar pagamento: {e}")

    logger.info(f"Timeout verificação automática para {transaction_id}")


# ─── Verificação manual de pagamento ────────────────────────────────────────

async def check_payment_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica o status de um pagamento consultando a PushinPay."""
    query = update.callback_query
    await query.answer("Verificando pagamento...")

    provider_transaction_id = query.data.split("_", 2)[2]

    transaction = await database.get_transaction_by_provider_id(provider_transaction_id)
    if not transaction:
        await query.answer("❌ Transação não encontrada.", show_alert=True)
        return

    api_status = await payment.check_transaction_status(provider_transaction_id)

    if api_status == "paid" and transaction["status"] == "pending":
        await database.mark_transaction_paid(provider_transaction_id)
        transaction["status"] = "paid"

    status_messages = {
        "pending":   "⏳ Pagamento ainda pendente. Aguardando confirmação.",
        "paid":      "✅ Pagamento confirmado! Processando entrega do eSIM...",
        "delivered": "🎉 eSIM entregue com sucesso!",
        "failed":    "❌ Pagamento falhou ou foi cancelado.",
    }

    status_msg = status_messages.get(transaction["status"], "❓ Status desconhecido.")

    message = (
        f"🔍 <b>Status da Transação</b>\n\n"
        f"ID: <code>{provider_transaction_id}</code>\n"
        f"Plano: {transaction['plan_name']}\n"
        f"Valor: R$ {transaction['amount_brl']:.2f}\n\n"
        f"{status_msg}"
    )

    keyboard = [
        [InlineKeyboardButton(
            "🔄 Verificar Novamente",
            callback_data=f"check_payment_{provider_transaction_id}",
        )],
        [InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")],
    ]

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ─── Registro dos handlers ───────────────────────────────────────────────────

def register_handlers(application):
    """Registra os handlers de compra."""
    application.add_handler(CallbackQueryHandler(buy_menu_callback,      pattern="^menu_buy$"))
    application.add_handler(CallbackQueryHandler(buy_plan_callback,      pattern="^buy_plan_"))
    application.add_handler(CallbackQueryHandler(pay_saldo_callback,     pattern="^pay_saldo_"))
    application.add_handler(CallbackQueryHandler(pay_pix_callback,       pattern="^pay_pix_"))
    application.add_handler(CallbackQueryHandler(check_payment_callback, pattern="^check_payment_"))
