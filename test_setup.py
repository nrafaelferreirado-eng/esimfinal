"""
Script de teste rápido para verificar a configuração.
Execute com: python test_setup.py
"""
import asyncio
import sys

def check_imports():
    """Verifica se todas as dependências estão instaladas."""
    print("🔍 Verificando dependências...")
    try:
        import telegram
        print("✅ python-telegram-bot instalado")
    except ImportError:
        print("❌ python-telegram-bot não encontrado")
        print("   Execute: pip install python-telegram-bot")
        return False
    
    try:
        import aiohttp
        print("✅ aiohttp instalado")
    except ImportError:
        print("❌ aiohttp não encontrado")
        print("   Execute: pip install aiohttp")
        return False
    
    try:
        import aiosqlite
        print("✅ aiosqlite instalado")
    except ImportError:
        print("❌ aiosqlite não encontrado")
        print("   Execute: pip install aiosqlite")
        return False
    
    return True


def check_config():
    """Verifica a configuração."""
    print("\n🔍 Verificando configuração...")
    try:
        import config
        
        issues = []
        
        if config.BOT_TOKEN == "YOUR_BOT_TOKEN_HERE":
            issues.append("BOT_TOKEN não configurado")
        else:
            print("✅ BOT_TOKEN configurado")
        
        if config.PUSHSHIPAY_API_TOKEN == "YOUR_PUSHSHIPAY_TOKEN_HERE":
            issues.append("PUSHSHIPAY_API_TOKEN não configurado")
        else:
            print("✅ PUSHSHIPAY_API_TOKEN configurado")
        
        if config.WEBHOOK_PUBLIC_URL == "https://your-domain.com/webhook/payment":
            issues.append("WEBHOOK_PUBLIC_URL não configurado")
        else:
            print("✅ WEBHOOK_PUBLIC_URL configurado")
        
        admin_ids = config.get_admin_ids()
        if not admin_ids:
            print("⚠️  ADMIN_IDS não configurado (você não terá acesso aos comandos admin)")
        else:
            print(f"✅ ADMIN_IDS configurado ({len(admin_ids)} admin(s))")
        
        if issues:
            print("\n❌ Problemas encontrados:")
            for issue in issues:
                print(f"   - {issue}")
            print("\nEdite config.py ou defina variáveis de ambiente.")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Erro ao verificar configuração: {e}")
        return False


async def check_database():
    """Verifica se o banco de dados pode ser inicializado."""
    print("\n🔍 Verificando banco de dados...")
    try:
        import database
        await database.init_db()
        print("✅ Banco de dados inicializado com sucesso")
        
        # Testar uma query simples
        plans = await database.list_plans(active_only=False)
        print(f"✅ Consulta ao banco funcionando ({len(plans)} plano(s) cadastrado(s))")
        
        return True
    except Exception as e:
        print(f"❌ Erro ao verificar banco de dados: {e}")
        return False


def main():
    """Função principal de teste."""
    print("=" * 60)
    print("🤖 Bot Telegram de Venda de eSIM - Teste de Configuração")
    print("=" * 60)
    
    # Verificar imports
    if not check_imports():
        print("\n❌ Instale as dependências antes de continuar:")
        print("   pip install -r requirements.txt")
        return 1
    
    # Verificar configuração
    config_ok = check_config()
    
    # Verificar banco de dados
    try:
        db_ok = asyncio.run(check_database())
    except Exception as e:
        print(f"❌ Erro ao testar banco de dados: {e}")
        db_ok = False
    
    # Resumo
    print("\n" + "=" * 60)
    if config_ok and db_ok:
        print("✅ TUDO PRONTO! Você pode iniciar o bot com:")
        print("   python main.py")
    else:
        print("❌ CORRIGIR PROBLEMAS ANTES DE INICIAR O BOT")
        print("   Veja as mensagens acima para detalhes")
    print("=" * 60)
    
    return 0 if (config_ok and db_ok) else 1


if __name__ == "__main__":
    sys.exit(main())
