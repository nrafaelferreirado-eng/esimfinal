# 🚀 Guia Rápido de Início

## Passo 1: Instalar Dependências

```bash
pip install -r requirements.txt
```

## Passo 2: Obter Token do Bot

1. Abra o Telegram
2. Procure por `@BotFather`
3. Envie `/newbot`
4. Siga as instruções
5. Copie o token fornecido

## Passo 3: Descobrir Seu Telegram ID

1. Procure por `@userinfobot` no Telegram
2. Envie `/start`
3. Copie o ID fornecido

## Passo 4: Configurar o Bot

Edite `config.py` e configure:

```python
BOT_TOKEN = "seu_token_aqui"
PUSHSHIPAY_API_TOKEN = "seu_token_pushshipay"
WEBHOOK_PUBLIC_URL = "https://seu-dominio.com/webhook/payment"
ADMIN_IDS = "seu_telegram_id"
```

## Passo 5: Testar Configuração

```bash
python test_setup.py
```

## Passo 6: Iniciar o Bot

```bash
python main.py
```

## Passo 7: Adicionar Planos

No Telegram, envie para o bot:

```
/admin_add_plan Europa 10GB | 10 | 59.90
/admin_add_plan América 5GB | 5 | 39.90
/admin_add_plan Ásia 15GB | 15 | 79.90
```

## Passo 8: Testar Compra

1. Envie `/start` para o bot
2. Clique em "🛒 Comprar eSIM"
3. Escolha um plano
4. Teste o fluxo de pagamento

---

## ⚠️ Importante para Produção

### Webhook Público

O bot precisa de uma URL pública para receber confirmações de pagamento.

**Opção 1: ngrok (teste local)**
```bash
ngrok http 8080
```
Copie a URL HTTPS e configure em `WEBHOOK_PUBLIC_URL`

**Opção 2: Servidor com IP público**
Configure um servidor com certificado SSL e aponte `WEBHOOK_PUBLIC_URL` para ele.

### Ajustar Integração PushShipay

Quando receber a documentação oficial da PushShipay:

1. Abra `payment.py`
2. Ajuste os endpoints e payloads conforme a doc
3. Ajuste `PUSHSHIPAY_BASE_URL` em `config.py`

---

## 📚 Comandos Admin

```
/admin_add_plan Nome | GB | Preço
/admin_list_plans
/admin_edit_plan ID | Nome | GB | Preço | active/inactive
/admin_remove_plan ID
/admin_add_admin TELEGRAM_ID
/admin_help
```

---

## 🆘 Problemas Comuns

**Bot não inicia:**
- Verifique se todas as variáveis em `config.py` estão configuradas
- Execute `python test_setup.py` para diagnóstico

**Webhook não recebe confirmações:**
- Verifique se a URL pública está acessível externamente
- Teste com: `curl -X POST sua-url/webhook/payment`

**Comandos admin não funcionam:**
- Verifique se seu Telegram ID está em `ADMIN_IDS`
- Use `@userinfobot` para confirmar seu ID

---

## 📖 Documentação Completa

Veja `README.md` para instruções detalhadas.

---

**Desenvolvido com ❤️**
