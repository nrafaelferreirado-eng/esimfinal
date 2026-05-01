"""
Handler para comando /start, menu inicial e fluxo de adicionar saldo via PIX.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes, CommandHandler, CallbackQueryHandler,
    MessageHandler, ConversationHandler, filters
)
import database
import payment
import logging

logger = logging.getLogger(__name__)

# Estado da conversa para adicionar saldo
AGUARDANDO_VALOR = 1


# ─── Helpers ─────────────────────────────────────────────────────────────────

DEFAULT_WELCOME_TEXT = (
    "━━━━━━━━━━━━━\n"
    "📱 <b>VITINHO STORE</b> 📱\n"
    "━━━━━━━━━━━━━\n\n"
    "Seja muito bem-vindo, <b>{first_name}</b>! Garantimos a melhor conexão e o melhor "
    "entretenimento para o seu dia a dia. Escolha a opção que mais combina com você:\n\n"
    "✨ <b>NOSSOS SERVIÇOS eSIM</b>\n"
    "Temos dois modos de ativação exclusivos:\n\n"
    "🚀 <b>Ativação Rápida:</b> Para quem não quer esperar. Conecte-se em instantes!\n\n"
    "⏳ <b>Ativação Lenta:</b> O melhor custo-benefício para quem busca economia.\n\n"
    "🎬 <b>STREAMING & CONTEÚDO</b>\n"
    "Confira nossa aba de Streaming logo abaixo para ver o estoque atualizado das melhores plataformas do mercado.\n\n"
    "📊 <b>STATUS DO ESTOQUE</b>\n"
    "📱 <b>{total_planos}</b> planos eSIM  |  📁 <b>{total_esims}</b> em estoque\n\n"
    "💡 Dúvidas? Clique no botão de Suporte abaixo e fale conosco agora mesmo!\n\n"
    "━━━━━━━━━━━━━\n"
    "<b>AGRADECEMOS A PREFERÊNCIA!</b>\n"
    "Escolha uma opção abaixo:"
)


async def _build_welcome(user, edit: bool = False):
    """Monta a mensagem de boas-vindas com estoque dinâmico."""
    estoque_lista = await database.get_estoque()
    total_planos = len(estoque_lista)
    total_esims  = sum(e.get("disponivel", 0) for e in estoque_lista)

    texto_salvo = await database.get_setting("texto_inicio") or DEFAULT_WELCOME_TEXT

    mensagem = texto_salvo.format(
        first_name=user.first_name,
        total_planos=total_planos,
        total_esims=total_esims,
    )

    keyboard = [
        [InlineKeyboardButton("🛒 Comprar eSIM",          callback_data="menu_buy")],
        [InlineKeyboardButton("🎬 Streaming & Conteúdo",  callback_data="menu_streaming")],
        [
            InlineKeyboardButton("👤 Meu Perfil",         callback_data="menu_profile"),
            InlineKeyboardButton("💰 Adicionar Saldo",    callback_data="menu_add_saldo"),
        ],
        [InlineKeyboardButton("🆘 Suporte",               callback_data="menu_suporte")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    return mensagem, reply_markup


# ─── /start ──────────────────────────────────────────────────────────────────

async def _verificar_membro_canal(bot, user_id: int) -> bool:
    """Verifica se o usuário é membro do canal configurado. Retorna True se for membro ou canal não configurado."""
    canal_id = await database.get_setting("canal_referencia_id")
    if not canal_id:
        return True  # Canal não configurado, libera acesso

    try:
        canal_id_int = int(canal_id)
    except (ValueError, TypeError):
        canal_id_int = canal_id

    try:
        membro = await bot.get_chat_member(chat_id=canal_id_int, user_id=user_id)
        return membro.status not in ("left", "kicked", "banned")
    except Exception:
        return True  # Em caso de erro, libera acesso


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler do comando /start."""
    user = update.effective_user

    # Verifica se é a primeira vez do usuário ANTES do upsert
    usuario_existente = await database.get_user(user.id)
    is_novo_usuario = usuario_existente is None

    # Cria/atualiza usuário no banco
    await database.upsert_user(
        telegram_id=user.id,
        username=user.username,
        first_name=user.first_name,
    )

    canal_url  = await database.get_setting("canal_referencia_url") or ""
    canal_nome = await database.get_setting("canal_referencia_nome") or "nosso canal"

    # Se for novo usuário, envia link do canal primeiro (independente de ser obrigatório)
    if is_novo_usuario and canal_url:
        keyboard_canal = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📢 Acessar {canal_nome}", url=canal_url)]
        ])
        await update.message.reply_text(
            f"👋 Olá, <b>{user.first_name}</b>! Seja bem-vindo!\n\n"
            f"📢 Antes de começar, entre no nosso canal para ver todas as vendas em tempo real e ficar por dentro das novidades:\n\n"
            f"👇 Clique no botão abaixo e depois volte aqui:",
            reply_markup=keyboard_canal,
            parse_mode="HTML",
        )

    # Verifica se o usuário entrou no canal (obrigatório)
    eh_membro = await _verificar_membro_canal(context.bot, user.id)
    if not eh_membro and canal_url:
        keyboard_canal = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📢 Entrar no {canal_nome}", url=canal_url)],
            [InlineKeyboardButton("✅ Já entrei!", callback_data="verificar_canal")],
        ])
        await update.message.reply_text(
            f"🔒 <b>Acesso restrito!</b>\n\n"
            f"Para usar o bot você precisa entrar no nosso canal primeiro:\n\n"
            f"1️⃣ Clique em <b>Entrar no {canal_nome}</b>\n"
            f"2️⃣ Entre no canal\n"
            f"3️⃣ Volte aqui e clique em <b>✅ Já entrei!</b>",
            reply_markup=keyboard_canal,
            parse_mode="HTML",
        )
        return

    # Exibe o menu principal
    mensagem, reply_markup = await _build_welcome(user)
    await update.message.reply_text(mensagem, reply_markup=reply_markup, parse_mode="HTML")


async def verificar_canal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica se o usuário entrou no canal após clicar em 'Já entrei'."""
    query = update.callback_query
    await query.answer()
    user = query.from_user

    canal_url  = await database.get_setting("canal_referencia_url") or ""
    canal_nome = await database.get_setting("canal_referencia_nome") or "nosso canal"

    eh_membro = await _verificar_membro_canal(context.bot, user.id)
    if not eh_membro:
        keyboard_canal = InlineKeyboardMarkup([
            [InlineKeyboardButton(f"📢 Entrar no {canal_nome}", url=canal_url)],
            [InlineKeyboardButton("✅ Já entrei!", callback_data="verificar_canal")],
        ])
        await query.edit_message_text(
            f"❌ <b>Você ainda não entrou no canal!</b>\n\n"
            f"Entre no canal e clique novamente em <b>✅ Já entrei!</b>",
            reply_markup=keyboard_canal,
            parse_mode="HTML",
        )
        return

    # Liberado! Exibe o menu
    mensagem, reply_markup = await _build_welcome(user)
    await query.edit_message_text(mensagem, reply_markup=reply_markup, parse_mode="HTML")


# ─── Menu principal (voltar) ─────────────────────────────────────────────────

async def main_menu_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Volta ao menu principal via inline button."""
    query = update.callback_query
    await query.answer()
    user = query.from_user
    mensagem, reply_markup = await _build_welcome(user)
    await query.edit_message_text(mensagem, reply_markup=reply_markup, parse_mode="HTML")


# ─── Suporte ─────────────────────────────────────────────────────────────────

async def suporte_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe informações de suporte."""
    query = update.callback_query
    await query.answer()

    username      = await database.get_setting("suporte_username") or "@suporte"
    whatsapp_url  = await database.get_setting("suporte_whatsapp") or ""
    telegram_url  = await database.get_setting("suporte_telegram_url") or ""

    mensagem = (
        f"🆘 <b>SUPORTE VITINHO STORE</b>\n\n"
        f"Precisa de ajuda? Fale diretamente com nossa equipe:\n\n"
        f"💬 Telegram: <b>{username}</b>\n"
    )

    if whatsapp_url:
        mensagem += f"📱 WhatsApp: disponível no botão abaixo\n"
    if telegram_url:
        mensagem += f"✈️ Telegram: disponível no botão abaixo\n"

    mensagem += f"\nRespondemos o mais rápido possível! 😊"

    keyboard = []
    botoes_contato = []
    if whatsapp_url:
        botoes_contato.append(InlineKeyboardButton("📱 Falar no WhatsApp", url=whatsapp_url))
    if telegram_url:
        botoes_contato.append(InlineKeyboardButton("✈️ Falar no Telegram", url=telegram_url))
    if botoes_contato:
        keyboard.append(botoes_contato)
    keyboard.append([InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")])

    await query.edit_message_text(
        mensagem,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


# ─── Adicionar Saldo via PIX ─────────────────────────────────────────────────

async def add_saldo_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe opções de valor para adicionar saldo."""
    query = update.callback_query
    await query.answer()

    saldo = await database.get_user_balance(query.from_user.id)

    mensagem = (
        f"💰 <b>ADICIONAR SALDO</b>\n\n"
        f"👛 Seu saldo atual: <b>R$ {saldo:.2f}</b>\n\n"
        f"Escolha um valor abaixo ou digite um valor personalizado:"
    )

    keyboard = [
        [
            InlineKeyboardButton("R$ 10",  callback_data="deposito_valor_10.0"),
            InlineKeyboardButton("R$ 20",  callback_data="deposito_valor_20.0"),
            InlineKeyboardButton("R$ 30",  callback_data="deposito_valor_30.0"),
        ],
        [
            InlineKeyboardButton("R$ 50",  callback_data="deposito_valor_50.0"),
            InlineKeyboardButton("R$ 100", callback_data="deposito_valor_100.0"),
            InlineKeyboardButton("R$ 200", callback_data="deposito_valor_200.0"),
        ],
        [InlineKeyboardButton("✏️ Outro valor", callback_data="deposito_custom")],
        [InlineKeyboardButton("⬅️ Voltar ao Menu",  callback_data="menu_main")],
    ]
    await query.edit_message_text(
        mensagem,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def deposito_valor_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gera PIX para o valor escolhido nos botões rápidos."""
    query = update.callback_query
    await query.answer()
    valor = float(query.data.split("_")[2])
    await _gerar_pix_deposito(query, context, valor)


async def deposito_custom_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Pede ao usuário para digitar o valor personalizado."""
    query = update.callback_query
    await query.answer()

    await query.edit_message_text(
        "✏️ <b>Valor personalizado</b>\n\n"
        "Digite o valor que deseja adicionar (mínimo R$ 5,00).\n"
        "Exemplo: <code>25</code> ou <code>37.50</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("❌ Cancelar", callback_data="menu_add_saldo")
        ]]),
    )
    return AGUARDANDO_VALOR


async def deposito_valor_digitado(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Recebe o valor digitado pelo usuário e gera o PIX."""
    texto = update.message.text.strip().replace(",", ".")
    try:
        valor = float(texto)
        if valor < 5:
            await update.message.reply_text(
                "❌ Valor mínimo é R$ 5,00. Digite novamente:",
                parse_mode="HTML",
            )
            return AGUARDANDO_VALOR
    except ValueError:
        await update.message.reply_text(
            "❌ Valor inválido. Digite apenas números. Ex: <code>25</code> ou <code>37.50</code>",
            parse_mode="HTML",
        )
        return AGUARDANDO_VALOR

    await _gerar_pix_deposito_msg(update, context, valor)
    return ConversationHandler.END


async def _gerar_pix_deposito(query, context, valor: float):
    user = query.from_user
    await query.edit_message_text(
        f"⏳ Gerando PIX de <b>R$ {valor:.2f}</b>...\n\nAguarde um momento.",
        parse_mode="HTML",
    )
    await _processar_pix_deposito(
        bot=context.bot,
        chat_id=user.id,
        user=user,
        valor=valor,
        edit_message=query.message,
    )


async def _gerar_pix_deposito_msg(update, context, valor: float):
    user = update.effective_user
    msg = await update.message.reply_text(
        f"⏳ Gerando PIX de <b>R$ {valor:.2f}</b>...\n\nAguarde um momento.",
        parse_mode="HTML",
    )
    await _processar_pix_deposito(
        bot=context.bot,
        chat_id=user.id,
        user=user,
        valor=valor,
        edit_message=msg,
    )


async def _processar_pix_deposito(bot, chat_id: int, user, valor: float, edit_message):
    """Lógica central: cria PIX de depósito e exibe QR Code."""
    try:
        charge_data = await payment.create_pix_charge(
            amount_brl=valor,
            description=f"Depósito de saldo - {user.first_name}",
            external_reference=f"deposito_user_{user.id}_{int(valor*100)}",
            customer_data={
                "telegram_id": user.id,
                "username":    user.username,
                "first_name":  user.first_name,
            },
        )

        transaction_id = await database.create_transaction(
            telegram_id=user.id,
            plan_id=0,
            amount_brl=valor,
            provider_transaction_id=charge_data["transaction_id"],
            plan_name="Depósito de Saldo",
            data_gb=0,
        )

        qr_base64 = charge_data.get("qr_code", "")
        copy_paste = charge_data.get("copy_paste_code", "")

        mensagem = (
            f"💰 <b>PIX gerado!</b>\n\n"
            f"Valor: <b>R$ {valor:.2f}</b>\n\n"
            f"Código Pix (copia e cola):\n"
            f"<code>{copy_paste}</code>\n\n"
            f"⏳ Após o pagamento, aguarde a confirmação automática."
        )

        keyboard = InlineKeyboardMarkup([[
            InlineKeyboardButton(
                "🔄 Verificar Pagamento",
                callback_data=f"check_deposito_{transaction_id}"
            )
        ]])

        if qr_base64:
            import base64
            import io
            img_bytes = base64.b64decode(qr_base64)
            await bot.send_photo(
                chat_id=chat_id,
                photo=io.BytesIO(img_bytes),
                caption=mensagem,
                reply_markup=keyboard,
                parse_mode="HTML",
            )
        else:
            await edit_message.edit_text(mensagem, reply_markup=keyboard, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Erro ao gerar PIX de depósito: {e}", exc_info=True)
        await edit_message.edit_text(
            f"❌ Erro ao gerar PIX: {str(e)}\n\nTente novamente mais tarde.",
            parse_mode="HTML",
        )


async def check_deposito_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verifica o status de um depósito."""
    query = update.callback_query
    await query.answer()

    transaction_id = int(query.data.split("_")[2])
    transaction = await database.get_transaction(transaction_id)

    if not transaction:
        await query.edit_message_text("❌ Transação não encontrada.")
        return

    if transaction["status"] == "paid":
        await query.edit_message_text(
            f"✅ <b>Pagamento confirmado!</b>\n\n"
            f"💰 R$ {transaction['amount_brl']:.2f} adicionado ao seu saldo.",
            parse_mode="HTML",
        )
        return

    # Verificar na API
    api_status = await payment.check_transaction_status(
        transaction["provider_transaction_id"]
    )

    if api_status == "paid" and transaction["status"] == "pending":
        await database.mark_transaction_paid(transaction_id)
        novo_saldo = await database.add_user_balance(query.from_user.id, transaction["amount_brl"])
        await query.edit_message_text(
            f"✅ <b>Pagamento confirmado!</b>\n\n"
            f"💰 R$ {transaction['amount_brl']:.2f} adicionado ao seu saldo.\n"
            f"👛 Saldo atual: <b>R$ {novo_saldo:.2f}</b>",
            reply_markup=InlineKeyboardMarkup([[
                InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")
            ]]),
            parse_mode="HTML",
        )
        return

    status_map = {
        "pending": "⏳ Pagamento ainda não confirmado. Aguarde alguns segundos e tente novamente.",
        "paid":    "✅ Pagamento já confirmado!",
        "failed":  "❌ Pagamento falhou ou foi cancelado.",
    }
    msg = status_map.get(transaction["status"], "❓ Status desconhecido.")

    await query.edit_message_text(
        f"🔍 <b>Status do Depósito</b>\n\n"
        f"💰 Valor: R$ {transaction['amount_brl']:.2f}\n\n"
        f"{msg}",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🔄 Verificar Novamente", callback_data=f"check_deposito_{transaction_id}")],
            [InlineKeyboardButton("⬅️ Voltar ao Menu",     callback_data="menu_main")],
        ]),
        parse_mode="HTML",
    )


# ─── Registro dos handlers ───────────────────────────────────────────────────

def register_handlers(application):
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CallbackQueryHandler(verificar_canal_callback, pattern="^verificar_canal$"))
    application.add_handler(CallbackQueryHandler(main_menu_callback,      pattern="^menu_main$"))
    application.add_handler(CallbackQueryHandler(suporte_callback,        pattern="^menu_suporte$"))
    application.add_handler(CallbackQueryHandler(add_saldo_callback,      pattern="^menu_add_saldo$"))
    application.add_handler(CallbackQueryHandler(deposito_valor_callback, pattern="^deposito_valor_"))
    application.add_handler(CallbackQueryHandler(deposito_custom_callback,pattern="^deposito_custom$"))
    application.add_handler(CallbackQueryHandler(check_deposito_callback, pattern="^check_deposito_"))

    conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(deposito_custom_callback, pattern="^deposito_custom$")],
        states={
            AGUARDANDO_VALOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, deposito_valor_digitado)
            ],
        },
        fallbacks=[
            CallbackQueryHandler(add_saldo_callback, pattern="^menu_add_saldo$"),
        ],
        per_message=False,
    )
    application.add_handler(conv)
