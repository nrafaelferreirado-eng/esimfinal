"""
Bot Telegram para venda de eSIM com pagamento PIX.
Entry point principal.
"""
import asyncio
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder

import config
import database
import webhook  # ← agora é o webhook_pushinpay.py renomeado para webhook.py
from handlers import start, profile, buy, admin, streaming

# Configurar logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def post_init(application):
    """Callback executado após inicialização do bot."""
    logger.info("Bot inicializado com sucesso")


async def post_shutdown(application):
    """Callback executado ao desligar o bot."""
    logger.info("Bot desligado")


async def handle_telegram_update(request):
    """Recebe updates do Telegram via webhook."""
    from aiohttp import web
    application = request.app["telegram_application"]
    try:
        data = await request.json()
        update = Update.de_json(data, application.bot)
        await application.process_update(update)
    except Exception as e:
        logger.error(f"Erro ao processar update do Telegram: {e}", exc_info=True)
    return web.json_response({"ok": True})


async def main():
    """Função principal."""
    try:
        # Validar configuração
        config.validate_config()
        logger.info("Configuração validada com sucesso")

        # Inicializar banco de dados
        await database.init_db()
        logger.info("Banco de dados inicializado")

        # Construir aplicação do bot
        application = (
            ApplicationBuilder()
            .token(config.BOT_TOKEN)
            .post_init(post_init)
            .post_shutdown(post_shutdown)
            .updater(None)  # Desabilita polling — usamos webhook
            .build()
        )

        # Registrar handlers
        start.register_handlers(application)
        profile.register_handlers(application)
        buy.register_handlers(application)
        admin.register_handlers(application)
        streaming.register_handlers(application)  # ✅ CORREÇÃO BUG 1: handler de streaming registrado
        logger.info("Handlers registrados")

        # Criar servidor webhook
        webhook_app = webhook.create_webhook_app(application.bot)
        webhook_app["telegram_application"] = application

        # ✅ Rota para updates do Telegram
        webhook_app.router.add_post("/telegram", handle_telegram_update)

        # ✅ Rota para confirmação de pagamento PIX (PushiPay) + entrega automática
        webhook_app.router.add_post(config.WEBHOOK_PATH, webhook.handle_webhook)

        webhook_runner = await webhook.start_webhook_server(
            webhook_app,
            config.WEBHOOK_HOST,
            config.WEBHOOK_PORT
        )
        logger.info(f"Servidor webhook iniciado em {config.WEBHOOK_HOST}:{config.WEBHOOK_PORT}")
        logger.info(f"Rota Telegram: /telegram")
        logger.info(f"Rota PIX:      {config.WEBHOOK_PATH}")
        logger.info(f"URL pública:   {config.WEBHOOK_PUBLIC_URL}")

        # Iniciar bot
        await application.initialize()
        await application.start()

        # Registrar webhook no Telegram
        telegram_base = config.WEBHOOK_PUBLIC_URL.rsplit("/webhook/payment", 1)[0]
        telegram_webhook_url = f"{telegram_base}/telegram"
        await application.bot.set_webhook(url=telegram_webhook_url)
        logger.info(f"✅ Webhook do Telegram registrado: {telegram_webhook_url}")
        logger.info(f"✅ Webhook PIX aguardando em: {config.WEBHOOK_PUBLIC_URL}")
        logger.info("✅ Bot rodando! Pressione Ctrl+C para parar.")

        # Manter rodando
        try:
            await asyncio.Event().wait()
        except (KeyboardInterrupt, SystemExit):
            logger.info("Recebido sinal de parada...")

        # Parar gracefully
        logger.info("Parando bot...")
        await application.bot.delete_webhook()
        await application.stop()
        await application.shutdown()

        await webhook_runner.cleanup()
        logger.info("✅ Bot encerrado com sucesso")

    except ValueError as e:
        logger.error(f"❌ Erro de configuração: {e}")
        logger.error("Por favor, configure as variáveis necessárias em config.py")
        return 1
    except Exception as e:
        logger.error(f"❌ Erro fatal: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    exit(exit_code)
