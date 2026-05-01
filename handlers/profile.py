"""
Handler para perfil do usuário e histórico de compras.
"""
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes, CallbackQueryHandler
import database
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


async def profile_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mostra o perfil do usuário."""
    query = update.callback_query
    await query.answer()
    
    user = query.from_user
    telegram_id = user.id
    
    # Buscar histórico de transações e saldo
    transactions = await database.list_user_transactions(telegram_id)
    saldo = await database.get_user_balance(telegram_id)
    
    # Montar mensagem
    message = (
        f"👤 <b>Seu Perfil</b>\n\n"
        f"🆔 ID Telegram: <code>{telegram_id}</code>\n"
        f"👛 Meu Saldo: <b>R$ {saldo:.2f}</b>\n"
        f"🛒 Total de compras: {len(transactions)}\n\n"
    )
    
    if transactions:
        message += "📦 <b>Histórico de Compras:</b>\n\n"
        
        # Limitar a últimas 10 transações para não estourar limite de mensagem
        for i, tx in enumerate(transactions[:10], 1):
            status_emoji = {
                "pending": "⏳",
                "paid": "✅",
                "delivered": "🎉",
                "failed": "❌"
            }.get(tx["status"], "❓")
            
            created_at = datetime.fromisoformat(tx["created_at"]).strftime("%d/%m/%Y %H:%M")

            # Detecta se é compra de streaming (plan_id == 0 com streaming no payload)
            plan_name = tx.get("plan_name") or "Streaming"
            data_gb   = tx.get("data_gb")
            if data_gb:
                descricao = f"{plan_name} ({data_gb} GB)"
            else:
                descricao = plan_name
            
            message += (
                f"{i}. {status_emoji} {descricao}\n"
                f"   R$ {tx['amount_brl']:.2f} - {tx['status'].upper()}\n"
                f"   {created_at}\n\n"
            )
        
        if len(transactions) > 10:
            message += f"... e mais {len(transactions) - 10} compra(s)\n"
    else:
        message += "Você ainda não realizou nenhuma compra."
    
    # Botão de voltar
    keyboard = [[InlineKeyboardButton("⬅️ Voltar ao Menu", callback_data="menu_main")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.edit_message_text(message, reply_markup=reply_markup, parse_mode="HTML")


def register_handlers(application):
    """Registra os handlers de perfil."""
    application.add_handler(CallbackQueryHandler(profile_callback, pattern="^menu_profile$"))
