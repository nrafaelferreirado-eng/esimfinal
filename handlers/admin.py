"""
Handler para comandos e menus administrativos — versão com botões interativos.
Inclui: Planos, Abastecimento (com foto), Estoque, Gestão de Admins,
        Gateway (token Pusshipay) e Gestão de Saldo de Clientes.
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ContextTypes,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ConversationHandler,
    filters,
)
import database

logger = logging.getLogger(__name__)

# ─── Estados da conversa ────────────────────────────────────────────────────
(
    MENU_PRINCIPAL,
    # Planos
    PLAN_AGUARDA_DADOS,
    PLAN_EDIT_ID,
    PLAN_EDIT_DADOS,
    PLAN_REMOVE_ID,
    # Abastecimento
    ABAST_ESCOLHE_PLANO,
    ABAST_AGUARDA_FOTO,
    ABAST_AGUARDA_QTD,
    # Admins
    ADMIN_NOVO_ID,
    ADMIN_REM_ID,
    # Broadcast
    BROADCAST_AGUARDA_MSG,
    # Gateway
    GATEWAY_AGUARDA_TOKEN,
    # Saldo
    SALDO_ADD_ID,
    SALDO_ADD_VALOR,
    SALDO_REM_ID,
    SALDO_REM_VALOR,
    SALDO_VER_ID,
    SUPORTE_AGUARDA_USERNAME,
    WHATSAPP_AGUARDA_URL,
    TELEGRAM_AGUARDA_URL,
    # Textos editáveis
    TEXTO_INICIO_AGUARDA,
    TEXTO_BUY_AGUARDA,
    TEXTO_STREAMING_AGUARDA,
    # Streaming
    STREAM_AGUARDA_SERVICO,
    STREAM_AGUARDA_PRECO,
    STREAM_AGUARDA_CRED,
    # Canal de referência
    CANAL_AGUARDA_URL,
    CANAL_AGUARDA_ID,
    CANAL_AGUARDA_NOME,
) = range(29)


# ─── Helpers ────────────────────────────────────────────────────────────────

async def check_admin(update: Update) -> bool:
    """Verifica se o usuário é administrador."""
    user_id = update.effective_user.id
    if not await database.is_admin(user_id):
        msg = update.message or update.callback_query.message
        await msg.reply_text("❌ Você não tem permissão para isso.")
        return False
    return True


def build_main_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [
            InlineKeyboardButton("📦 Planos",        callback_data="menu_planos"),
            InlineKeyboardButton("🛢 Abastecimento", callback_data="menu_abast"),
        ],
        [
            InlineKeyboardButton("📊 Estoque",       callback_data="menu_estoque"),
            InlineKeyboardButton("👤 Admins",        callback_data="menu_admins"),
        ],
        [
            InlineKeyboardButton("📣 Broadcast",     callback_data="menu_broadcast"),
            InlineKeyboardButton("🔑 Gateway",       callback_data="menu_gateway"),
        ],
        [
            InlineKeyboardButton("🎬 Streaming",       callback_data="menu_streaming_adm"),
        ],
        [
            InlineKeyboardButton("💰 Saldo Clientes", callback_data="menu_saldo"),
            InlineKeyboardButton("⚙️ Config",          callback_data="menu_config"),
            InlineKeyboardButton("❓ Ajuda",           callback_data="menu_ajuda"),
        ],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_planos_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ Criar Plano",    callback_data="plan_criar")],
        [InlineKeyboardButton("📋 Listar Planos",  callback_data="plan_listar")],
        [InlineKeyboardButton("✏️ Editar Plano",   callback_data="plan_editar")],
        [InlineKeyboardButton("🗑 Remover Plano",  callback_data="plan_remover")],
        [InlineKeyboardButton("🔙 Voltar",         callback_data="menu_principal")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_abast_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ Abastecer Plano",    callback_data="abast_novo")],
        [InlineKeyboardButton("📋 Ver Abastecimentos", callback_data="abast_listar")],
        [InlineKeyboardButton("🔙 Voltar",             callback_data="menu_principal")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_estoque_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📊 Ver Estoque Atual", callback_data="estoque_ver")],
        [InlineKeyboardButton("🔙 Voltar",            callback_data="menu_principal")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_admins_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ Adicionar Admin",  callback_data="admin_add")],
        [InlineKeyboardButton("📋 Listar Admins",    callback_data="admin_list")],
        [InlineKeyboardButton("🗑 Remover Admin",    callback_data="admin_rem")],
        [InlineKeyboardButton("🔙 Voltar",           callback_data="menu_principal")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_gateway_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("🔄 Alterar Token Pusshipay", callback_data="gateway_alterar")],
        [InlineKeyboardButton("👁 Ver Token Atual",         callback_data="gateway_ver")],
        [InlineKeyboardButton("🔙 Voltar",                  callback_data="menu_principal")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_saldo_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("➕ Adicionar Saldo",  callback_data="saldo_add")],
        [InlineKeyboardButton("➖ Retirar Saldo",    callback_data="saldo_rem")],
        [InlineKeyboardButton("👁 Ver Saldo",        callback_data="saldo_ver")],
        [InlineKeyboardButton("🔙 Voltar",           callback_data="menu_principal")],
    ]
    return InlineKeyboardMarkup(keyboard)


def build_cancelar_btn() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton("❌ Cancelar", callback_data="cancelar")]])


# ─── Entrada: /admin ────────────────────────────────────────────────────────

async def admin_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return ConversationHandler.END

    await update.message.reply_text(
        "🔧 <b>Painel Administrativo</b>\n\nEscolha uma opção abaixo:",
        parse_mode="HTML",
        reply_markup=build_main_menu(),
    )
    return MENU_PRINCIPAL


# ─── Menu Principal ─────────────────────────────────────────────────────────

async def menu_principal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🔧 <b>Painel Administrativo</b>\n\nEscolha uma opção:",
        parse_mode="HTML",
        reply_markup=build_main_menu(),
    )
    return MENU_PRINCIPAL


async def menu_planos_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📦 <b>Gestão de Planos</b>\n\nO que deseja fazer?",
        parse_mode="HTML",
        reply_markup=build_planos_menu(),
    )
    return MENU_PRINCIPAL


async def menu_abast_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🛢 <b>Abastecimento</b>\n\nAqui você pode abastecer planos com imagens de arquivo.",
        parse_mode="HTML",
        reply_markup=build_abast_menu(),
    )
    return MENU_PRINCIPAL


async def menu_estoque_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📊 <b>Estoque</b>\n\nVisualize o estoque disponível por plano.",
        parse_mode="HTML",
        reply_markup=build_estoque_menu(),
    )
    return MENU_PRINCIPAL


async def menu_admins_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "👤 <b>Administradores</b>\n\nGerencie quem tem acesso ao painel.",
        parse_mode="HTML",
        reply_markup=build_admins_menu(),
    )
    return MENU_PRINCIPAL


async def menu_ajuda_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    texto = (
        "❓ <b>Ajuda — Painel Admin</b>\n\n"
        "📦 <b>Planos</b> — Crie, edite ou remova planos de dados.\n\n"
        "🛢 <b>Abastecimento</b> — Envie a foto do arquivo de credenciais para abastecer um plano.\n\n"
        "📊 <b>Estoque</b> — Veja quantas credenciais disponíveis há por plano.\n\n"
        "👤 <b>Admins</b> — Adicione ou veja quem são os admins do bot.\n\n"
        "📣 <b>Broadcast</b> — Envie mensagens ou fotos para todos os usuários.\n\n"
        "🔑 <b>Gateway</b> — Altere o token da Pusshipay sem reiniciar o bot.\n\n"
        "💰 <b>Saldo Clientes</b> — Adicione, retire ou consulte saldo de qualquer usuário pelo ID.\n\n"
        "Use /admin para abrir este painel a qualquer momento."
    )
    await q.edit_message_text(
        texto,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="menu_principal")]]),
    )
    return MENU_PRINCIPAL


# ─── PLANOS ─────────────────────────────────────────────────────────────────

async def plan_criar_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "➕ <b>Criar Plano</b>\n\n"
        "Envie os dados no formato:\n"
        "<code>Nome | GB | Preço</code>\n\n"
        "Exemplo:\n<code>Europa 10GB | 10 | 59.90</code>",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return PLAN_AGUARDA_DADOS


async def plan_recebe_dados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        parts = [p.strip() for p in update.message.text.split("|")]
        if len(parts) != 3:
            raise ValueError("Formato inválido")

        name = parts[0]
        data_gb = int(parts[1])
        price_brl = float(parts[2])

        if data_gb <= 0 or price_brl <= 0:
            raise ValueError("GB e Preço devem ser positivos")

        plan_id = await database.create_plan(name, data_gb, price_brl)

        await update.message.reply_text(
            f"✅ <b>Plano criado!</b>\n\n"
            f"🆔 ID: <code>{plan_id}</code>\n"
            f"📦 Nome: {name}\n"
            f"📊 Dados: {data_gb} GB\n"
            f"💰 Preço: R$ {price_brl:.2f}",
            parse_mode="HTML",
            reply_markup=build_planos_menu(),
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Erro: {e}\n\nFormato correto:\n<code>Nome | GB | Preço</code>",
            parse_mode="HTML",
            reply_markup=build_cancelar_btn(),
        )
        return PLAN_AGUARDA_DADOS

    return MENU_PRINCIPAL


async def plan_listar_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plans = await database.list_plans(active_only=False)
    if not plans:
        texto = "📋 Nenhum plano cadastrado ainda."
    else:
        texto = "📋 <b>Planos Cadastrados:</b>\n\n"
        for p in plans:
            icone = "✅" if p["is_active"] else "❌"
            texto += (
                f"{icone} <b>{p['name']}</b> | ID: <code>{p['id']}</code>\n"
                f"   📊 {p['data_gb']} GB  💰 R$ {p['price_brl']:.2f}\n\n"
            )

    await q.edit_message_text(
        texto,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Planos", callback_data="menu_planos")]]),
    )
    return MENU_PRINCIPAL


async def plan_editar_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "✏️ <b>Editar Plano</b>\n\nDigite o <b>ID</b> do plano que deseja editar:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return PLAN_EDIT_ID


async def plan_edit_recebe_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        plan_id = int(update.message.text.strip())
        plan = await database.get_plan(plan_id)
        if not plan:
            await update.message.reply_text(f"❌ Plano ID {plan_id} não encontrado.", reply_markup=build_cancelar_btn())
            return PLAN_EDIT_ID

        context.user_data["edit_plan_id"] = plan_id
        await update.message.reply_text(
            f"✏️ Editando: <b>{plan['name']}</b>\n\n"
            "Envie os novos dados:\n"
            "<code>Nome | GB | Preço | Status</code>\n\n"
            "Status: <code>active</code> ou <code>inactive</code>\n"
            f"Exemplo: <code>{plan['name']} | {plan['data_gb']} | {plan['price_brl']:.2f} | active</code>",
            parse_mode="HTML",
            reply_markup=build_cancelar_btn(),
        )
        return PLAN_EDIT_DADOS
    except ValueError:
        await update.message.reply_text("❌ ID inválido.", reply_markup=build_cancelar_btn())
        return PLAN_EDIT_ID


async def plan_edit_recebe_dados(update: Update, context: ContextTypes.DEFAULT_TYPE):
    plan_id = context.user_data.get("edit_plan_id")
    try:
        parts = [p.strip() for p in update.message.text.split("|")]
        if len(parts) != 4:
            raise ValueError("São necessários 4 campos")

        name = parts[0]
        data_gb = int(parts[1])
        price_brl = float(parts[2])
        status = parts[3].lower()

        if status not in ("active", "inactive"):
            raise ValueError("Status deve ser 'active' ou 'inactive'")

        is_active = status == "active"
        await database.update_plan(plan_id, name, data_gb, price_brl, is_active)

        await update.message.reply_text(
            f"✅ <b>Plano atualizado!</b>\n\n"
            f"📦 {name} | {data_gb} GB | R$ {price_brl:.2f} | {'Ativo' if is_active else 'Inativo'}",
            parse_mode="HTML",
            reply_markup=build_planos_menu(),
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Erro: {e}\n\nFormato: <code>Nome | GB | Preço | Status</code>",
            parse_mode="HTML",
            reply_markup=build_cancelar_btn(),
        )
        return PLAN_EDIT_DADOS

    return MENU_PRINCIPAL


async def plan_remover_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🗑 <b>Remover Plano</b>\n\nDigite o <b>ID</b> do plano a remover:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return PLAN_REMOVE_ID


async def plan_remove_recebe_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        plan_id = int(update.message.text.strip())
        plan = await database.get_plan(plan_id)
        if not plan:
            await update.message.reply_text(f"❌ Plano ID {plan_id} não encontrado.", reply_markup=build_cancelar_btn())
            return PLAN_REMOVE_ID

        await database.delete_plan(plan_id)
        await update.message.reply_text(
            f"✅ Plano <b>{plan['name']}</b> removido!",
            parse_mode="HTML",
            reply_markup=build_planos_menu(),
        )
    except ValueError:
        await update.message.reply_text("❌ ID inválido.", reply_markup=build_cancelar_btn())
        return PLAN_REMOVE_ID

    return MENU_PRINCIPAL


# ─── ABASTECIMENTO ──────────────────────────────────────────────────────────

async def abast_novo_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plans = await database.list_plans(active_only=True)
    if not plans:
        await q.edit_message_text(
            "❌ Nenhum plano ativo. Crie um plano primeiro.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="menu_abast")]]),
        )
        return MENU_PRINCIPAL

    keyboard = [
        [InlineKeyboardButton(f"📦 {p['name']} ({p['data_gb']}GB)", callback_data=f"abast_plan_{p['id']}")]
        for p in plans
    ]
    keyboard.append([InlineKeyboardButton("🔙 Cancelar", callback_data="cancelar")])

    await q.edit_message_text(
        "🛢 <b>Abastecer Plano</b>\n\nSelecione o plano que deseja abastecer:",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )
    return ABAST_ESCOLHE_PLANO


async def abast_escolhe_plano_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    plan_id = int(q.data.split("_")[-1])
    plan = await database.get_plan(plan_id)
    context.user_data["abast_plan_id"] = plan_id
    context.user_data["abast_plan_name"] = plan["name"]

    await q.edit_message_text(
        f"🛢 Abastecendo: <b>{plan['name']}</b>\n\n"
        "📸 Envie agora a <b>foto/imagem</b> do arquivo de credenciais deste plano.",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return ABAST_AGUARDA_FOTO


async def abast_recebe_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.photo:
        file_id = update.message.photo[-1].file_id
    elif update.message.document and update.message.document.mime_type.startswith("image/"):
        file_id = update.message.document.file_id
    else:
        await update.message.reply_text(
            "❌ Por favor, envie uma imagem (foto ou arquivo de imagem).",
            reply_markup=build_cancelar_btn(),
        )
        return ABAST_AGUARDA_FOTO

    context.user_data["abast_foto_file_id"] = file_id

    await update.message.reply_text(
        "✅ Imagem recebida!\n\n"
        "Agora informe a <b>quantidade de credenciais</b> neste arquivo:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return ABAST_AGUARDA_QTD


async def abast_recebe_qtd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        qtd = int(update.message.text.strip())
        if qtd <= 0:
            raise ValueError("Quantidade deve ser positiva")

        plan_id = context.user_data["abast_plan_id"]
        plan_name = context.user_data["abast_plan_name"]
        foto_file_id = context.user_data["abast_foto_file_id"]

        await database.add_abastecimento(
            plan_id=plan_id,
            foto_file_id=foto_file_id,
            quantidade=qtd,
            admin_id=update.effective_user.id,
        )

        await update.message.reply_text(
            f"✅ <b>Abastecimento registrado!</b>\n\n"
            f"📦 Plano: {plan_name}\n"
            f"📊 Quantidade adicionada: {qtd}\n"
            f"👤 Admin: {update.effective_user.full_name}",
            parse_mode="HTML",
            reply_markup=build_abast_menu(),
        )
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {e}\n\nDigite apenas um número inteiro.",
            reply_markup=build_cancelar_btn(),
        )
        return ABAST_AGUARDA_QTD

    return MENU_PRINCIPAL


async def abast_listar_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    registros = await database.list_abastecimentos()
    if not registros:
        texto = "📋 Nenhum abastecimento registrado ainda."
    else:
        texto = "📋 <b>Últimos Abastecimentos:</b>\n\n"
        for r in registros[-10:]:
            texto += (
                f"📦 {r.get('plan_name', '?')} | +{r['quantidade']} creds\n"
                f"   🕐 {r.get('created_at', '')}\n\n"
            )

    await q.edit_message_text(
        texto,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Abastecimento", callback_data="menu_abast")]]),
    )
    return MENU_PRINCIPAL


# ─── ESTOQUE ────────────────────────────────────────────────────────────────

async def estoque_ver_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    try:
        estoque = await database.get_estoque()
        if not estoque:
            texto = "📊 Estoque vazio ou nenhum plano cadastrado."
        else:
            texto = "📊 <b>Estoque Atual:</b>\n\n"
            for item in estoque:
                barra = "🟩" * min(item["disponivel"] // 5, 10)
                barra = barra or "🟥"
                texto += (
                    f"📦 <b>{item['plan_name']}</b>\n"
                    f"   Disponível: {item['disponivel']}  {barra}\n\n"
                )
    except Exception:
        texto = "⚠️ Função de estoque ainda não implementada no database."

    await q.edit_message_text(
        texto,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Voltar", callback_data="menu_principal")]]),
    )
    return MENU_PRINCIPAL


# ─── ADMINS ─────────────────────────────────────────────────────────────────

async def admin_add_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "➕ <b>Adicionar Admin</b>\n\nDigite o <b>Telegram ID</b> do novo administrador:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return ADMIN_NOVO_ID


async def admin_recebe_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        novo_id = int(update.message.text.strip())
        await database.add_admin(novo_id)
        await update.message.reply_text(
            f"✅ Admin <code>{novo_id}</code> adicionado com sucesso!",
            parse_mode="HTML",
            reply_markup=build_admins_menu(),
        )
    except ValueError:
        await update.message.reply_text("❌ ID inválido. Use apenas números.", reply_markup=build_cancelar_btn())
        return ADMIN_NOVO_ID

    return MENU_PRINCIPAL


async def admin_list_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    try:
        from config import get_admin_ids
        donos = get_admin_ids()
        admins = await database.list_admins()

        texto = "👤 <b>Administradores:</b>\n\n"

        # Mostra donos fixos do .env
        for d in donos:
            texto += f"👑 <code>{d}</code>  <i>(dono — fixo no .env)</i>\n"

        # Mostra admins adicionados pelo bot
        extras = [a for a in admins if a["telegram_id"] not in donos]
        if extras:
            texto += "\n"
            for i, a in enumerate(extras, 1):
                texto += f"{i}. <code>{a['telegram_id']}</code>\n"
        elif not donos:
            texto = "👤 Nenhum admin cadastrado."
    except Exception as e:
        texto = f"⚠️ Erro ao listar admins: {e}"

    await q.edit_message_text(
        texto,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑 Remover Admin", callback_data="admin_rem")],
            [InlineKeyboardButton("🔙 Admins",        callback_data="menu_admins")],
        ]),
    )
    return MENU_PRINCIPAL


async def admin_rem_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🗑 <b>Remover Admin</b>\n\nDigite o <b>Telegram ID</b> do administrador a remover:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return ADMIN_REM_ID


async def admin_rem_recebe_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        rem_id = int(update.message.text.strip())

        # Impede remover o dono fixo definido no .env
        from config import get_admin_ids
        if rem_id in get_admin_ids():
            await update.message.reply_text(
                f"⛔ O ID <code>{rem_id}</code> é o dono do bot (definido no .env) e não pode ser removido por aqui.",
                parse_mode="HTML",
                reply_markup=build_admins_menu(),
            )
            return MENU_PRINCIPAL

        await database.remove_admin(rem_id)
        await update.message.reply_text(
            f"✅ Admin <code>{rem_id}</code> removido com sucesso!",
            parse_mode="HTML",
            reply_markup=build_admins_menu(),
        )
    except ValueError:
        await update.message.reply_text("❌ ID inválido. Use apenas números.", reply_markup=build_cancelar_btn())
        return ADMIN_REM_ID

    return MENU_PRINCIPAL


# ─── BROADCAST ──────────────────────────────────────────────────────────────

def build_broadcast_menu() -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📝 Enviar Mensagem de Texto", callback_data="broadcast_texto")],
        [InlineKeyboardButton("🖼 Enviar Foto + Legenda",    callback_data="broadcast_foto")],
        [InlineKeyboardButton("🔙 Voltar",                   callback_data="menu_principal")],
    ]
    return InlineKeyboardMarkup(keyboard)


async def menu_broadcast_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "📣 <b>Broadcast</b>\n\nEnvie uma mensagem para <b>todos os usuários</b> do bot.",
        parse_mode="HTML",
        reply_markup=build_broadcast_menu(),
    )
    return MENU_PRINCIPAL


async def broadcast_texto_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["broadcast_tipo"] = "texto"
    await q.edit_message_text(
        "📝 <b>Broadcast — Texto</b>\n\n"
        "Digite a mensagem que será enviada para todos os usuários:\n\n"
        "💡 Você pode usar HTML: <code>&lt;b&gt;negrito&lt;/b&gt;</code>, <code>&lt;i&gt;itálico&lt;/i&gt;</code>",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return BROADCAST_AGUARDA_MSG


async def broadcast_foto_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data["broadcast_tipo"] = "foto"
    await q.edit_message_text(
        "🖼 <b>Broadcast — Foto</b>\n\n"
        "Envie a foto com a legenda desejada.\n"
        "A legenda é opcional.",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return BROADCAST_AGUARDA_MSG


async def broadcast_recebe_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    tipo = context.user_data.get("broadcast_tipo", "texto")

    if tipo == "foto":
        if update.message.photo:
            file_id = update.message.photo[-1].file_id
        elif update.message.document and update.message.document.mime_type and update.message.document.mime_type.startswith("image/"):
            file_id = update.message.document.file_id
        else:
            await update.message.reply_text(
                "❌ Por favor, envie uma imagem (foto ou arquivo de imagem).",
                reply_markup=build_cancelar_btn(),
            )
            return BROADCAST_AGUARDA_MSG

        legenda = update.message.caption or ""
        context.user_data["broadcast_foto_id"] = file_id
        context.user_data["broadcast_legenda"] = legenda
    else:
        texto = update.message.text
        context.user_data["broadcast_texto_msg"] = texto

    if tipo == "foto":
        preview = f"🖼 Foto com legenda: {context.user_data.get('broadcast_legenda') or '(sem legenda)'}"
    else:
        preview = f"📝 Mensagem:\n{context.user_data.get('broadcast_texto_msg', '')[:200]}"

    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Confirmar e Enviar", callback_data="broadcast_confirmar")],
        [InlineKeyboardButton("❌ Cancelar",           callback_data="cancelar")],
    ])
    await update.message.reply_text(
        f"📣 <b>Confirmar Broadcast</b>\n\n{preview}\n\nDeseja enviar para todos os usuários?",
        parse_mode="HTML",
        reply_markup=keyboard,
    )
    return BROADCAST_AGUARDA_MSG


async def broadcast_confirmar_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer("Enviando... aguarde ⏳")

    tipo     = context.user_data.get("broadcast_tipo", "texto")
    bot      = q.get_bot()
    usuarios = await database.list_all_users()

    enviados = 0
    falhas   = 0

    await q.edit_message_text(
        f"📣 Enviando broadcast para {len(usuarios)} usuários... ⏳",
        parse_mode="HTML",
    )

    for user in usuarios:
        tid = user if isinstance(user, int) else user.get("telegram_id")
        try:
            if tipo == "foto":
                await bot.send_photo(
                    chat_id=tid,
                    photo=context.user_data["broadcast_foto_id"],
                    caption=context.user_data.get("broadcast_legenda") or None,
                    parse_mode="HTML",
                )
            else:
                await bot.send_message(
                    chat_id=tid,
                    text=context.user_data["broadcast_texto_msg"],
                    parse_mode="HTML",
                )
            enviados += 1
        except Exception as e:
            logger.warning(f"Broadcast falhou para {tid}: {e}")
            falhas += 1

    context.user_data.clear()

    await bot.send_message(
        chat_id=q.from_user.id,
        text=(
            f"✅ <b>Broadcast concluído!</b>\n\n"
            f"📨 Enviados: {enviados}\n"
            f"❌ Falhas: {falhas}\n"
            f"👥 Total: {len(usuarios)}"
        ),
        parse_mode="HTML",
        reply_markup=build_main_menu(),
    )
    return MENU_PRINCIPAL


# ─── GATEWAY (Token Pusshipay) ───────────────────────────────────────────────

async def menu_gateway_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🔑 <b>Gateway — Pusshipay</b>\n\n"
        "Gerencie o token de integração com a Pusshipay.",
        parse_mode="HTML",
        reply_markup=build_gateway_menu(),
    )
    return MENU_PRINCIPAL


async def gateway_ver_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()

    try:
        token = await database.get_pusshipay_token()
        if token:
            # Exibe apenas os últimos 8 caracteres por segurança
            token_mask = "••••••••••••" + token[-8:]
            texto = (
                f"🔑 <b>Token Pusshipay Atual:</b>\n\n"
                f"<code>{token_mask}</code>\n\n"
                f"<i>Apenas os últimos 8 caracteres são exibidos por segurança.</i>"
            )
        else:
            texto = "⚠️ Nenhum token configurado ainda."
    except Exception as e:
        texto = f"⚠️ Erro ao buscar token: {e}"

    await q.edit_message_text(
        texto,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Gateway", callback_data="menu_gateway")]]),
    )
    return MENU_PRINCIPAL


async def gateway_alterar_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "🔄 <b>Alterar Token Pusshipay</b>\n\n"
        "Digite o <b>novo token</b> da Pusshipay:\n\n"
        "⚠️ <i>O token será salvo imediatamente e usado em todas as próximas transações.</i>",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return GATEWAY_AGUARDA_TOKEN


async def gateway_recebe_token(update: Update, context: ContextTypes.DEFAULT_TYPE):
    novo_token = update.message.text.strip()

    if len(novo_token) < 10:
        await update.message.reply_text(
            "❌ Token muito curto. Verifique e tente novamente.",
            reply_markup=build_cancelar_btn(),
        )
        return GATEWAY_AGUARDA_TOKEN

    try:
        await database.set_pusshipay_token(novo_token)
        token_mask = "••••••••••••" + novo_token[-8:]
        await update.message.reply_text(
            f"✅ <b>Token atualizado com sucesso!</b>\n\n"
            f"🔑 Novo token: <code>{token_mask}</code>\n\n"
            f"<i>O bot já está usando o novo token para processar pagamentos.</i>",
            parse_mode="HTML",
            reply_markup=build_gateway_menu(),
        )
    except Exception as e:
        await update.message.reply_text(
            f"❌ Erro ao salvar token: {e}",
            reply_markup=build_cancelar_btn(),
        )
        return GATEWAY_AGUARDA_TOKEN

    return MENU_PRINCIPAL


# ─── SALDO CLIENTES ─────────────────────────────────────────────────────────

async def menu_saldo_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "💰 <b>Saldo de Clientes</b>\n\n"
        "Gerencie o saldo de qualquer usuário pelo ID do Telegram.",
        parse_mode="HTML",
        reply_markup=build_saldo_menu(),
    )
    return MENU_PRINCIPAL


# ── Adicionar Saldo ──

async def saldo_add_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "➕ <b>Adicionar Saldo</b>\n\n"
        "Digite o <b>Telegram ID</b> do cliente:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return SALDO_ADD_ID


async def saldo_add_recebe_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text.strip())
        context.user_data["saldo_target_id"] = user_id

        # Tenta buscar saldo atual para confirmar que o usuário existe
        try:
            saldo_atual = await database.get_user_balance(user_id)
            info = f"💰 Saldo atual: R$ {saldo_atual:.2f}"
        except Exception:
            info = "⚠️ Usuário não encontrado no banco, mas o saldo será criado."

        await update.message.reply_text(
            f"➕ <b>Adicionar Saldo</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"{info}\n\n"
            f"Digite o <b>valor a adicionar</b> (ex: <code>50.00</code>):",
            parse_mode="HTML",
            reply_markup=build_cancelar_btn(),
        )
        return SALDO_ADD_VALOR
    except ValueError:
        await update.message.reply_text("❌ ID inválido. Use apenas números.", reply_markup=build_cancelar_btn())
        return SALDO_ADD_ID


async def saldo_add_recebe_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(update.message.text.strip().replace(",", "."))
        if valor <= 0:
            raise ValueError("Valor deve ser positivo")

        user_id = context.user_data["saldo_target_id"]
        novo_saldo = await database.add_user_balance(user_id, valor)

        await update.message.reply_text(
            f"✅ <b>Saldo adicionado!</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"➕ Valor adicionado: R$ {valor:.2f}\n"
            f"💰 Novo saldo: R$ {novo_saldo:.2f}\n\n"
            f"👤 Admin: {update.effective_user.full_name}",
            parse_mode="HTML",
            reply_markup=build_saldo_menu(),
        )
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {e}\n\nDigite um valor numérico positivo (ex: <code>50.00</code>).",
            parse_mode="HTML",
            reply_markup=build_cancelar_btn(),
        )
        return SALDO_ADD_VALOR
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}", reply_markup=build_cancelar_btn())
        return SALDO_ADD_VALOR

    return MENU_PRINCIPAL


# ── Retirar Saldo ──

async def saldo_rem_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "➖ <b>Retirar Saldo</b>\n\n"
        "Digite o <b>Telegram ID</b> do cliente:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return SALDO_REM_ID


async def saldo_rem_recebe_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text.strip())
        context.user_data["saldo_target_id"] = user_id

        try:
            saldo_atual = await database.get_user_balance(user_id)
            info = f"💰 Saldo atual: R$ {saldo_atual:.2f}"
        except Exception:
            info = "⚠️ Usuário não encontrado no banco."

        await update.message.reply_text(
            f"➖ <b>Retirar Saldo</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"{info}\n\n"
            f"Digite o <b>valor a retirar</b> (ex: <code>20.00</code>):",
            parse_mode="HTML",
            reply_markup=build_cancelar_btn(),
        )
        return SALDO_REM_VALOR
    except ValueError:
        await update.message.reply_text("❌ ID inválido. Use apenas números.", reply_markup=build_cancelar_btn())
        return SALDO_REM_ID


async def saldo_rem_recebe_valor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        valor = float(update.message.text.strip().replace(",", "."))
        if valor <= 0:
            raise ValueError("Valor deve ser positivo")

        user_id = context.user_data["saldo_target_id"]
        novo_saldo = await database.remove_user_balance(user_id, valor)

        await update.message.reply_text(
            f"✅ <b>Saldo retirado!</b>\n\n"
            f"👤 ID: <code>{user_id}</code>\n"
            f"➖ Valor retirado: R$ {valor:.2f}\n"
            f"💰 Novo saldo: R$ {novo_saldo:.2f}\n\n"
            f"👤 Admin: {update.effective_user.full_name}",
            parse_mode="HTML",
            reply_markup=build_saldo_menu(),
        )
    except ValueError as e:
        await update.message.reply_text(
            f"❌ {e}\n\nDigite um valor numérico positivo (ex: <code>20.00</code>).",
            parse_mode="HTML",
            reply_markup=build_cancelar_btn(),
        )
        return SALDO_REM_VALOR
    except Exception as e:
        await update.message.reply_text(f"❌ Erro: {e}", reply_markup=build_cancelar_btn())
        return SALDO_REM_VALOR

    return MENU_PRINCIPAL


# ── Ver Saldo ──

async def saldo_ver_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    await q.edit_message_text(
        "👁 <b>Ver Saldo</b>\n\n"
        "Digite o <b>Telegram ID</b> do cliente:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return SALDO_VER_ID


async def saldo_ver_recebe_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        user_id = int(update.message.text.strip())

        try:
            saldo = await database.get_user_balance(user_id)
            # Tenta pegar nome do usuário se disponível
            try:
                user_info = await database.get_user(user_id)
                nome = user_info.get("full_name") or user_info.get("name") or "—"
                username = f"@{user_info['username']}" if user_info.get("username") else "—"
            except Exception:
                nome = "—"
                username = "—"

            texto = (
                f"💰 <b>Saldo do Cliente</b>\n\n"
                f"👤 ID: <code>{user_id}</code>\n"
                f"📛 Nome: {nome}\n"
                f"🔗 Username: {username}\n"
                f"💵 Saldo: R$ {saldo:.2f}"
            )
        except Exception as e:
            texto = f"❌ Não foi possível buscar o saldo: {e}"

        await update.message.reply_text(
            texto,
            parse_mode="HTML",
            reply_markup=build_saldo_menu(),
        )
    except ValueError:
        await update.message.reply_text("❌ ID inválido. Use apenas números.", reply_markup=build_cancelar_btn())
        return SALDO_VER_ID

    return MENU_PRINCIPAL


# ─── CANCELAR ───────────────────────────────────────────────────────────────



# ─── Gestão de Streaming (Admin) ────────────────────────────────────────────

def build_streaming_adm_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("➕ Adicionar Conta",    callback_data="stream_adm_add")],
        [InlineKeyboardButton("📊 Ver Estoque",        callback_data="stream_adm_estoque")],
        [InlineKeyboardButton("🔙 Voltar",             callback_data="menu_principal")],
    ])


async def menu_streaming_adm_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    await q.edit_message_text(
        "🎬 <b>Gestão de Streaming</b>\n\nEscolha uma opção:",
        parse_mode="HTML",
        reply_markup=build_streaming_adm_menu(),
    )
    return MENU_PRINCIPAL


async def stream_adm_estoque_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL

    estoque = await database.get_estoque_streaming()
    if not estoque:
        texto = "📊 <b>Estoque de Streaming</b>\n\nNenhuma conta cadastrada ainda."
    else:
        texto = "📊 <b>Estoque de Streaming</b>\n\n"
        for s in estoque:
            texto += f"🎬 <b>{s['servico']}</b> — R$ {s['preco_brl']:.2f} | {s['disponivel']}/{s['total']} disponíveis\n"

    await q.edit_message_text(
        texto,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Streaming", callback_data="menu_streaming_adm")]]),
    )
    return MENU_PRINCIPAL


async def stream_adm_add_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    await q.edit_message_text(
        "➕ <b>Adicionar Conta de Streaming</b>\n\n"
        "Digite o <b>nome do serviço</b>:\n"
        "Exemplo: <code>Netflix</code>, <code>Disney+</code>, <code>Spotify</code>",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return STREAM_AGUARDA_SERVICO


async def stream_adm_recebe_servico(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return MENU_PRINCIPAL
    servico = update.message.text.strip()
    context.user_data["stream_servico"] = servico
    await update.message.reply_text(
        f"✅ Serviço: <b>{servico}</b>\n\n"
        f"Agora digite o <b>preço</b> em reais:\n"
        f"Exemplo: <code>25.90</code>",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return STREAM_AGUARDA_PRECO


async def stream_adm_recebe_preco(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return MENU_PRINCIPAL
    texto = update.message.text.strip().replace(",", ".")
    try:
        preco = float(texto)
        if preco <= 0:
            raise ValueError
    except ValueError:
        await update.message.reply_text(
            "❌ Preço inválido. Digite apenas números. Ex: <code>25.90</code>",
            parse_mode="HTML",
        )
        return STREAM_AGUARDA_PRECO

    context.user_data["stream_preco"] = preco
    servico = context.user_data.get("stream_servico", "")
    await update.message.reply_text(
        f"✅ Preço: <b>R$ {preco:.2f}</b>\n\n"
        f"Agora envie as credenciais no formato:\n"
        f"<code>email@exemplo.com:senha123</code>\n\n"
        f"(email e senha separados por <b>:</b>)",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return STREAM_AGUARDA_CRED


async def stream_adm_recebe_cred(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return MENU_PRINCIPAL
    texto = update.message.text.strip()
    if ":" not in texto:
        await update.message.reply_text(
            "❌ Formato inválido. Use: <code>email:senha</code>",
            parse_mode="HTML",
        )
        return STREAM_AGUARDA_CRED

    partes = texto.split(":", 1)
    email = partes[0].strip()
    senha = partes[1].strip()
    servico = context.user_data.get("stream_servico", "")
    preco   = context.user_data.get("stream_preco", 0.0)

    await database.add_conta_streaming(
        servico=servico,
        preco_brl=preco,
        email=email,
        senha=senha,
        admin_id=update.effective_user.id,
    )

    context.user_data.clear()
    await update.message.reply_text(
        f"✅ <b>Conta adicionada com sucesso!</b>\n\n"
        f"🎬 Serviço: {servico}\n"
        f"💰 Preço: R$ {preco:.2f}\n"
        f"📧 Email: <code>{email}</code>\n"
        f"🔑 Senha: <code>{senha}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[
            InlineKeyboardButton("➕ Adicionar Outra", callback_data="stream_adm_add"),
            InlineKeyboardButton("🔙 Streaming",       callback_data="menu_streaming_adm"),
        ]]),
    )
    return MENU_PRINCIPAL


# ─── Configurações (Suporte) ────────────────────────────────────────────────

def build_config_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ Alterar @ do Suporte",       callback_data="config_suporte")],
        [InlineKeyboardButton("📱 Alterar URL do WhatsApp",    callback_data="config_whatsapp")],
        [InlineKeyboardButton("✈️ Alterar URL do Telegram",    callback_data="config_telegram")],
        [InlineKeyboardButton("👁 Ver configurações",          callback_data="config_suporte_ver")],
        [InlineKeyboardButton("📝 Editar Texto Inicial (/start)", callback_data="config_texto_inicio")],
        [InlineKeyboardButton("🛒 Editar Texto Comprar eSIM",  callback_data="config_texto_buy")],
        [InlineKeyboardButton("🎬 Editar Texto Streaming",     callback_data="config_texto_streaming")],
        [InlineKeyboardButton("📢 Configurar Canal",           callback_data="config_canal")],
        [InlineKeyboardButton("🔙 Voltar",                     callback_data="menu_principal")],
    ])


async def menu_config_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    await q.edit_message_text(
        "⚙️ <b>Configurações</b>\n\nEscolha uma opção:",
        parse_mode="HTML",
        reply_markup=build_config_menu(),
    )
    return MENU_PRINCIPAL


async def config_suporte_ver_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    username      = await database.get_setting("suporte_username") or "Não configurado"
    whatsapp_url  = await database.get_setting("suporte_whatsapp") or "Não configurado"
    telegram_url  = await database.get_setting("suporte_telegram_url") or "Não configurado"
    await q.edit_message_text(
        f"⚙️ <b>Configurações de Suporte</b>\n\n"
        f"💬 Telegram @: <code>{username}</code>\n"
        f"📱 WhatsApp: <code>{whatsapp_url}</code>\n"
        f"✈️ Telegram URL: <code>{telegram_url}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config", callback_data="menu_config")]]),
    )
    return MENU_PRINCIPAL


async def config_suporte_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    username_atual = await database.get_setting("suporte_username") or "Não configurado"
    await q.edit_message_text(
        f"✏️ <b>Alterar @ do Suporte</b>\n\n"
        f"Atual: <code>{username_atual}</code>\n\n"
        f"Digite o novo @ do suporte (com ou sem @).\n"
        f"Exemplo: <code>@VitinhoSuporte</code> ou <code>VitinhoSuporte</code>",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return SUPORTE_AGUARDA_USERNAME


async def config_suporte_recebe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return MENU_PRINCIPAL
    texto = update.message.text.strip()
    # Garante que começa com @
    if not texto.startswith("@"):
        texto = "@" + texto
    await database.set_setting("suporte_username", texto)
    await update.message.reply_text(
        f"✅ <b>@ do Suporte atualizado!</b>\n\n"
        f"Novo valor: <code>{texto}</code>\n\n"
        f"O botão Suporte no /start já vai usar esse @.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config", callback_data="menu_config")]]),
    )
    return MENU_PRINCIPAL


async def config_whatsapp_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    url_atual = await database.get_setting("suporte_whatsapp") or "Não configurado"
    await q.edit_message_text(
        f"📱 <b>Alterar URL do WhatsApp</b>\n\n"
        f"Atual: <code>{url_atual}</code>\n\n"
        f"Cole a URL do WhatsApp (ex: <code>https://wa.me/5511999999999</code>).",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return WHATSAPP_AGUARDA_URL


async def config_whatsapp_recebe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return MENU_PRINCIPAL
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text(
            "❌ URL inválida. Deve começar com <code>https://</code>\n\nEx: <code>https://wa.me/5511999999999</code>\n\nDigite novamente:",
            parse_mode="HTML",
        )
        return WHATSAPP_AGUARDA_URL
    await database.set_setting("suporte_whatsapp", url)
    await update.message.reply_text(
        f"✅ <b>URL do WhatsApp atualizada!</b>\n\n"
        f"Nova URL: <code>{url}</code>\n\n"
        f"O botão WhatsApp no Suporte já vai usar essa URL.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config", callback_data="menu_config")]]),
    )
    return MENU_PRINCIPAL


async def config_telegram_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    url_atual = await database.get_setting("suporte_telegram_url") or "Não configurado"
    await q.edit_message_text(
        f"✈️ <b>Alterar URL do Telegram de Suporte</b>\n\n"
        f"Atual: <code>{url_atual}</code>\n\n"
        f"Cole o link do Telegram de suporte.\n"
        f"Exemplo: <code>https://t.me/VitinhoSuporte</code>",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return TELEGRAM_AGUARDA_URL


async def config_telegram_recebe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return MENU_PRINCIPAL
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text(
            "❌ URL inválida. Deve começar com <code>https://</code>\n\nEx: <code>https://t.me/VitinhoSuporte</code>\n\nDigite novamente:",
            parse_mode="HTML",
        )
        return TELEGRAM_AGUARDA_URL
    await database.set_setting("suporte_telegram_url", url)
    await update.message.reply_text(
        f"✅ <b>URL do Telegram atualizada!</b>\n\n"
        f"Nova URL: <code>{url}</code>\n\n"
        f"O botão Telegram no Suporte já vai usar essa URL.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config", callback_data="menu_config")]]),
    )
    return MENU_PRINCIPAL


# ─── Edição de textos editáveis ────────────────────────────────────────────

async def config_texto_inicio_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    atual = await database.get_setting("texto_inicio") or "(padrão do sistema)"
    preview = atual[:300] + "..." if len(atual) > 300 else atual
    await q.edit_message_text(
        f"📝 <b>Editar Texto Inicial (/start)</b>\n\n"
        f"<b>Texto atual (prévia):</b>\n<code>{preview}</code>\n\n"
        f"⚠️ Use <code>{{first_name}}</code> para o nome do usuário, "
        f"<code>{{total_planos}}</code> e <code>{{total_esims}}</code> para o estoque.\n\n"
        f"Digite o novo texto completo:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return TEXTO_INICIO_AGUARDA


async def config_texto_inicio_recebe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return MENU_PRINCIPAL
    texto = update.message.text.strip()
    await database.set_setting("texto_inicio", texto)
    await update.message.reply_text(
        f"✅ <b>Texto Inicial atualizado!</b>\n\n"
        f"O próximo /start já vai usar o novo texto.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config", callback_data="menu_config")]]),
    )
    return MENU_PRINCIPAL


async def config_texto_buy_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    atual = await database.get_setting("texto_comprar_esim") or "🛒 <b>Planos Disponíveis</b>\n\nEscolha um plano para comprar:\n\n"
    preview = atual[:300] + "..." if len(atual) > 300 else atual
    await q.edit_message_text(
        f"🛒 <b>Editar Texto da Aba Comprar eSIM</b>\n\n"
        f"<b>Texto atual:</b>\n<code>{preview}</code>\n\n"
        f"Digite o novo texto que aparece no cabeçalho da lista de planos:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return TEXTO_BUY_AGUARDA


async def config_texto_buy_recebe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return MENU_PRINCIPAL
    texto = update.message.text.strip()
    await database.set_setting("texto_comprar_esim", texto)
    await update.message.reply_text(
        f"✅ <b>Texto Comprar eSIM atualizado!</b>\n\n"
        f"A aba de compra já vai usar o novo texto.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config", callback_data="menu_config")]]),
    )
    return MENU_PRINCIPAL


async def config_texto_streaming_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL
    atual = await database.get_setting("texto_streaming") or "🎬 <b>STREAMING & CONTEÚDO</b>\n\nEscolha o serviço desejado:\n\n"
    preview = atual[:300] + "..." if len(atual) > 300 else atual
    await q.edit_message_text(
        f"🎬 <b>Editar Texto da Aba Streaming</b>\n\n"
        f"<b>Texto atual:</b>\n<code>{preview}</code>\n\n"
        f"Digite o novo texto que aparece no cabeçalho da lista de serviços:",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return TEXTO_STREAMING_AGUARDA


async def config_texto_streaming_recebe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_admin(update):
        return MENU_PRINCIPAL
    texto = update.message.text.strip()
    await database.set_setting("texto_streaming", texto)
    await update.message.reply_text(
        f"✅ <b>Texto Streaming atualizado!</b>\n\n"
        f"A aba de streaming já vai usar o novo texto.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Config", callback_data="menu_config")]]),
    )
    return MENU_PRINCIPAL



# ─── CANAL DE REFERÊNCIA ─────────────────────────────────────────────────────

async def config_canal_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Exibe menu de configuração do canal de referência."""
    q = update.callback_query
    await q.answer()
    if not await check_admin(update):
        return MENU_PRINCIPAL

    canal_url  = await database.get_setting("canal_referencia_url")  or "Não configurado"
    canal_id   = await database.get_setting("canal_referencia_id")   or "Não configurado"
    canal_nome = await database.get_setting("canal_referencia_nome") or "Não configurado"

    texto = (
        "📢 <b>Canal de Referência</b>\n\n"
        f"🔗 URL do canal: <code>{canal_url}</code>\n"
        f"🆔 ID do canal: <code>{canal_id}</code>\n"
        f"📛 Nome do canal: <code>{canal_nome}</code>\n\n"
        "ℹ️ A URL é enviada para novos clientes no /start.\n"
        "ℹ️ O ID é usado para postar vendas automaticamente.\n\n"
        "O que deseja configurar?"
    )
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🔗 Alterar URL do Canal",  callback_data="canal_url")],
        [InlineKeyboardButton("🆔 Alterar ID do Canal",   callback_data="canal_id")],
        [InlineKeyboardButton("📛 Alterar Nome do Canal", callback_data="canal_nome")],
        [InlineKeyboardButton("🔙 Config",                callback_data="menu_config")],
    ])
    await q.edit_message_text(texto, parse_mode="HTML", reply_markup=keyboard)
    return MENU_PRINCIPAL


async def canal_url_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    atual = await database.get_setting("canal_referencia_url") or "Não configurado"
    await q.edit_message_text(
        f"🔗 <b>URL do Canal</b>\n\nAtual: <code>{atual}</code>\n\n"
        f"Cole o link do canal (ex: <code>https://t.me/seucanal</code>):",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return CANAL_AGUARDA_URL


async def canal_url_recebe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    if not url.startswith("http"):
        await update.message.reply_text("❌ URL inválida. Deve começar com http. Tente novamente:")
        return CANAL_AGUARDA_URL
    await database.set_setting("canal_referencia_url", url)
    await update.message.reply_text(
        f"✅ <b>URL do canal atualizada!</b>\n\n<code>{url}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Canal", callback_data="config_canal")]]),
    )
    return MENU_PRINCIPAL


async def canal_id_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    atual = await database.get_setting("canal_referencia_id") or "Não configurado"
    await q.edit_message_text(
        f"🆔 <b>ID do Canal</b>\n\nAtual: <code>{atual}</code>\n\n"
        f"Cole o ID do canal (ex: <code>-1001234567890</code>).\n\n"
        f"💡 Como obter: adicione o bot como admin do canal, envie uma mensagem lá e veja nos logs do Railway.",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return CANAL_AGUARDA_ID


async def canal_id_recebe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    texto = update.message.text.strip()
    # Aceita número negativo (canal) ou @username
    if not (texto.lstrip("-").isdigit() or texto.startswith("@")):
        await update.message.reply_text(
            "❌ ID inválido. Use o número negativo do canal (ex: -1001234567890) ou @username. Tente novamente:"
        )
        return CANAL_AGUARDA_ID
    await database.set_setting("canal_referencia_id", texto)
    await update.message.reply_text(
        f"✅ <b>ID do canal atualizado!</b>\n\n<code>{texto}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Canal", callback_data="config_canal")]]),
    )
    return MENU_PRINCIPAL


async def canal_nome_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    atual = await database.get_setting("canal_referencia_nome") or "Não configurado"
    await q.edit_message_text(
        f"📛 <b>Nome do Canal</b>\n\nAtual: <code>{atual}</code>\n\n"
        f"Digite o nome que aparece no botão enviado ao novo cliente (ex: <code>Vitinho Store Vendas</code>):",
        parse_mode="HTML",
        reply_markup=build_cancelar_btn(),
    )
    return CANAL_AGUARDA_NOME


async def canal_nome_recebe(update: Update, context: ContextTypes.DEFAULT_TYPE):
    nome = update.message.text.strip()
    await database.set_setting("canal_referencia_nome", nome)
    await update.message.reply_text(
        f"✅ <b>Nome do canal atualizado!</b>\n\n<code>{nome}</code>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Canal", callback_data="config_canal")]]),
    )
    return MENU_PRINCIPAL


async def cancelar_cb(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    context.user_data.clear()
    await q.edit_message_text(
        "🔧 <b>Painel Administrativo</b>\n\nOperação cancelada. Escolha uma opção:",
        parse_mode="HTML",
        reply_markup=build_main_menu(),
    )
    return MENU_PRINCIPAL


# ─── Registro dos Handlers ──────────────────────────────────────────────────

def register_handlers(application):
    conv = ConversationHandler(
        entry_points=[CommandHandler("admin", admin_start)],
        states={
            MENU_PRINCIPAL: [
                CallbackQueryHandler(menu_principal_cb,   pattern="^menu_principal$"),
                CallbackQueryHandler(menu_planos_cb,      pattern="^menu_planos$"),
                CallbackQueryHandler(menu_abast_cb,       pattern="^menu_abast$"),
                CallbackQueryHandler(menu_estoque_cb,     pattern="^menu_estoque$"),
                CallbackQueryHandler(menu_admins_cb,      pattern="^menu_admins$"),
                CallbackQueryHandler(menu_ajuda_cb,       pattern="^menu_ajuda$"),
                # Planos
                CallbackQueryHandler(plan_criar_cb,       pattern="^plan_criar$"),
                CallbackQueryHandler(plan_listar_cb,      pattern="^plan_listar$"),
                CallbackQueryHandler(plan_editar_cb,      pattern="^plan_editar$"),
                CallbackQueryHandler(plan_remover_cb,     pattern="^plan_remover$"),
                # Abastecimento
                CallbackQueryHandler(abast_novo_cb,       pattern="^abast_novo$"),
                CallbackQueryHandler(abast_listar_cb,     pattern="^abast_listar$"),
                # Estoque
                CallbackQueryHandler(estoque_ver_cb,      pattern="^estoque_ver$"),
                # Admins
                CallbackQueryHandler(admin_add_cb,        pattern="^admin_add$"),
                CallbackQueryHandler(admin_list_cb,       pattern="^admin_list$"),
                CallbackQueryHandler(admin_rem_cb,        pattern="^admin_rem$"),
                # Broadcast
                CallbackQueryHandler(menu_broadcast_cb,   pattern="^menu_broadcast$"),
                CallbackQueryHandler(broadcast_texto_cb,  pattern="^broadcast_texto$"),
                CallbackQueryHandler(broadcast_foto_cb,   pattern="^broadcast_foto$"),
                # Gateway
                CallbackQueryHandler(menu_gateway_cb,     pattern="^menu_gateway$"),
                CallbackQueryHandler(gateway_ver_cb,      pattern="^gateway_ver$"),
                CallbackQueryHandler(gateway_alterar_cb,  pattern="^gateway_alterar$"),
                # Streaming admin
                CallbackQueryHandler(menu_streaming_adm_cb,  pattern="^menu_streaming_adm$"),
                CallbackQueryHandler(stream_adm_add_cb,       pattern="^stream_adm_add$"),
                CallbackQueryHandler(stream_adm_estoque_cb,   pattern="^stream_adm_estoque$"),
                # Config
                CallbackQueryHandler(menu_config_cb,      pattern="^menu_config$"),
                CallbackQueryHandler(config_suporte_cb,   pattern="^config_suporte$"),
                CallbackQueryHandler(config_suporte_ver_cb, pattern="^config_suporte_ver$"),
                CallbackQueryHandler(config_canal_cb,      pattern="^config_canal$"),
                CallbackQueryHandler(canal_url_cb,         pattern="^canal_url$"),
                CallbackQueryHandler(canal_id_cb,          pattern="^canal_id$"),
                CallbackQueryHandler(canal_nome_cb,        pattern="^canal_nome$"),
                CallbackQueryHandler(config_whatsapp_cb,    pattern="^config_whatsapp$"),
                CallbackQueryHandler(config_telegram_cb,        pattern="^config_telegram$"),
                CallbackQueryHandler(config_texto_inicio_cb,    pattern="^config_texto_inicio$"),
                CallbackQueryHandler(config_texto_buy_cb,       pattern="^config_texto_buy$"),
                CallbackQueryHandler(config_texto_streaming_cb, pattern="^config_texto_streaming$"),
                # Saldo
                CallbackQueryHandler(menu_saldo_cb,       pattern="^menu_saldo$"),
                CallbackQueryHandler(saldo_add_cb,        pattern="^saldo_add$"),
                CallbackQueryHandler(saldo_rem_cb,        pattern="^saldo_rem$"),
                CallbackQueryHandler(saldo_ver_cb,        pattern="^saldo_ver$"),
                # Cancelar
                CallbackQueryHandler(cancelar_cb,         pattern="^cancelar$"),
            ],
            PLAN_AGUARDA_DADOS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, plan_recebe_dados),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            PLAN_EDIT_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, plan_edit_recebe_id),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            PLAN_EDIT_DADOS: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, plan_edit_recebe_dados),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            PLAN_REMOVE_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, plan_remove_recebe_id),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            ABAST_ESCOLHE_PLANO: [
                CallbackQueryHandler(abast_escolhe_plano_cb, pattern="^abast_plan_"),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            ABAST_AGUARDA_FOTO: [
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, abast_recebe_foto),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            ABAST_AGUARDA_QTD: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, abast_recebe_qtd),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            ADMIN_NOVO_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_recebe_id),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            ADMIN_REM_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, admin_rem_recebe_id),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            BROADCAST_AGUARDA_MSG: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, broadcast_recebe_msg),
                MessageHandler(filters.PHOTO | filters.Document.IMAGE, broadcast_recebe_msg),
                CallbackQueryHandler(broadcast_confirmar_cb, pattern="^broadcast_confirmar$"),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            GATEWAY_AGUARDA_TOKEN: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, gateway_recebe_token),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            SALDO_ADD_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, saldo_add_recebe_id),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            SALDO_ADD_VALOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, saldo_add_recebe_valor),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            SALDO_REM_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, saldo_rem_recebe_id),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            SALDO_REM_VALOR: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, saldo_rem_recebe_valor),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            SALDO_VER_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, saldo_ver_recebe_id),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            SUPORTE_AGUARDA_USERNAME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, config_suporte_recebe),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            WHATSAPP_AGUARDA_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, config_whatsapp_recebe),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            TELEGRAM_AGUARDA_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, config_telegram_recebe),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            TEXTO_INICIO_AGUARDA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, config_texto_inicio_recebe),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            TEXTO_BUY_AGUARDA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, config_texto_buy_recebe),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            TEXTO_STREAMING_AGUARDA: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, config_texto_streaming_recebe),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            STREAM_AGUARDA_SERVICO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stream_adm_recebe_servico),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            STREAM_AGUARDA_PRECO: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stream_adm_recebe_preco),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            STREAM_AGUARDA_CRED: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, stream_adm_recebe_cred),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            CANAL_AGUARDA_URL: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, canal_url_recebe),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            CANAL_AGUARDA_ID: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, canal_id_recebe),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
            CANAL_AGUARDA_NOME: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, canal_nome_recebe),
                CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
            ],
        },
        fallbacks=[
            CommandHandler("admin", admin_start),
            CallbackQueryHandler(cancelar_cb, pattern="^cancelar$"),
        ],
        per_message=False,
    )

    application.add_handler(conv)
    application.add_handler(CommandHandler("testcanal", testcanal_command))


# ─── Comando /testcanal ──────────────────────────────────────────────────────

async def testcanal_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Testa o envio de mensagem no canal de referência."""
    if not await check_admin(update):
        return

    canal_id_raw = await database.get_setting("canal_referencia_id")
    canal_url    = await database.get_setting("canal_referencia_url") or "Não configurado"
    canal_nome   = await database.get_setting("canal_referencia_nome") or "Não configurado"

    if not canal_id_raw:
        await update.message.reply_text(
            "❌ Canal não configurado!\n\n"
            "Vá em /admin → ⚙️ Config → 📢 Configurar Canal e preencha o ID do canal."
        )
        return

    try:
        canal_id = int(canal_id_raw)
    except (ValueError, TypeError):
        canal_id = canal_id_raw

    await update.message.reply_text(
        f"🔍 Tentando enviar mensagem de teste...\n\n"
        f"🆔 ID: <code>{canal_id}</code>\n"
        f"🔗 URL: {canal_url}\n"
        f"📛 Nome: {canal_nome}",
        parse_mode="HTML"
    )

    try:
        await context.bot.send_message(
            chat_id=canal_id,
            text="✅ <b>Teste de notificação!</b>\n\nO bot está configurado corretamente para postar neste canal.",
            parse_mode="HTML",
        )
        await update.message.reply_text("✅ <b>Mensagem enviada com sucesso!</b> Verifique o canal.", parse_mode="HTML")
    except Exception as e:
        await update.message.reply_text(
            f"❌ <b>Falhou!</b>\n\n"
            f"Erro: <code>{type(e).__name__}: {e}</code>\n\n"
            f"Possíveis causas:\n"
            f"• Bot não é admin do canal\n"
            f"• ID do canal errado\n"
            f"• Bot foi removido do canal",
            parse_mode="HTML"
        )
