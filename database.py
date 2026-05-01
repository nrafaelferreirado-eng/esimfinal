"""
Camada de banco de dados com SQLite e aiosqlite.
"""
import aiosqlite
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
import config


async def init_db():
    """Inicializa o banco de dados e cria as tabelas necessárias."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        # Tabela de usuários
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Tabela de planos
        await db.execute("""
            CREATE TABLE IF NOT EXISTS plans (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                data_gb INTEGER NOT NULL,
                price_brl REAL NOT NULL,
                is_active INTEGER DEFAULT 1,
                delivery_template TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Tabela de transações
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                plan_id INTEGER NOT NULL,
                provider_transaction_id TEXT UNIQUE,
                amount_brl REAL NOT NULL,
                status TEXT NOT NULL,
                qr_code TEXT,
                copy_paste_code TEXT,
                provider_payload TEXT,
                delivery_payload TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                paid_at TEXT,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id),
                FOREIGN KEY (plan_id) REFERENCES plans(id)
            )
        """)

        # Tabela de admins
        await db.execute("""
            CREATE TABLE IF NOT EXISTS admins (
                telegram_id INTEGER PRIMARY KEY,
                created_at TEXT NOT NULL
            )
        """)

        # Tabela de estoque de fotos (abastecimento para entrega automática)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS estoque_fotos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plan_id INTEGER NOT NULL,
                foto_file_id TEXT NOT NULL,
                quantidade INTEGER NOT NULL DEFAULT 1,
                usado INTEGER NOT NULL DEFAULT 0,
                admin_id INTEGER,
                created_at TEXT NOT NULL,
                FOREIGN KEY (plan_id) REFERENCES plans(id)
            )
        """)

        # Tabela de saldo dos usuários
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_balances (
                telegram_id INTEGER PRIMARY KEY,
                balance REAL NOT NULL DEFAULT 0.0,
                updated_at TEXT NOT NULL,
                FOREIGN KEY (telegram_id) REFERENCES users(telegram_id)
            )
        """)

        # Tabela de configurações gerais (token gateway, etc.)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)


        # Tabela de contas de streaming
        await db.execute("""
            CREATE TABLE IF NOT EXISTS contas_streaming (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                servico TEXT NOT NULL,
                preco_brl REAL NOT NULL DEFAULT 0.0,
                email TEXT NOT NULL,
                senha TEXT NOT NULL,
                usado INTEGER NOT NULL DEFAULT 0,
                telegram_id_comprador INTEGER,
                admin_id INTEGER,
                created_at TEXT NOT NULL,
                vendido_at TEXT
            )
        """)

        await db.commit()


# ========== Operações de usuários ==========

async def upsert_user(telegram_id: int, username: Optional[str], first_name: Optional[str]):
    """Cria ou atualiza um usuário."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, username, first_name, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                username = excluded.username,
                first_name = excluded.first_name,
                updated_at = excluded.updated_at
        """, (telegram_id, username, first_name, now, now))
        await db.commit()


async def get_user(telegram_id: int) -> Optional[Dict[str, Any]]:
    """Busca um usuário por ID."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM users WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def list_user_transactions(telegram_id: int) -> List[Dict[str, Any]]:
    """Lista todas as transações de um usuário."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT t.*, p.name as plan_name, p.data_gb
            FROM transactions t
            JOIN plans p ON t.plan_id = p.id
            WHERE t.telegram_id = ?
            ORDER BY t.created_at DESC
        """, (telegram_id,)) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ========== Operações de planos ==========

async def create_plan(name: str, data_gb: int, price_brl: float, delivery_template: Optional[str] = None):
    """Cria um novo plano."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO plans (name, data_gb, price_brl, is_active, delivery_template, created_at, updated_at)
            VALUES (?, ?, ?, 1, ?, ?, ?)
        """, (name, data_gb, price_brl, delivery_template, now, now))
        await db.commit()
        return cursor.lastrowid


async def list_plans(active_only: bool = True) -> List[Dict[str, Any]]:
    """Lista todos os planos."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        query = "SELECT * FROM plans"
        if active_only:
            query += " WHERE is_active = 1"
        query += " ORDER BY price_brl ASC"

        async with db.execute(query) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_plan(plan_id: int) -> Optional[Dict[str, Any]]:
    """Busca um plano por ID."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT * FROM plans WHERE id = ?", (plan_id,)) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_plan(plan_id: int, name: Optional[str] = None, data_gb: Optional[int] = None,
                      price_brl: Optional[float] = None, is_active: Optional[bool] = None,
                      delivery_template: Optional[str] = None):
    """Atualiza um plano existente."""
    now = datetime.utcnow().isoformat()
    updates = []
    params = []

    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if data_gb is not None:
        updates.append("data_gb = ?")
        params.append(data_gb)
    if price_brl is not None:
        updates.append("price_brl = ?")
        params.append(price_brl)
    if is_active is not None:
        updates.append("is_active = ?")
        params.append(1 if is_active else 0)
    if delivery_template is not None:
        updates.append("delivery_template = ?")
        params.append(delivery_template)

    if not updates:
        return

    updates.append("updated_at = ?")
    params.append(now)
    params.append(plan_id)

    query = f"UPDATE plans SET {', '.join(updates)} WHERE id = ?"

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(query, params)
        await db.commit()


async def delete_plan(plan_id: int):
    """Remove um plano (soft delete - marca como inativo)."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "UPDATE plans SET is_active = 0, updated_at = ? WHERE id = ?",
            (now, plan_id)
        )
        await db.commit()


# ========== Operações de admins ==========

async def add_admin(telegram_id: int):
    """Adiciona um administrador."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT OR IGNORE INTO admins (telegram_id, created_at)
            VALUES (?, ?)
        """, (telegram_id, now))
        await db.commit()


async def list_admins() -> list:
    """Lista todos os administradores como dicts com telegram_id."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("SELECT telegram_id FROM admins") as cursor:
            rows = await cursor.fetchall()
            return [{"telegram_id": row[0]} for row in rows]


async def remove_admin(telegram_id: int):
    """Remove um administrador pelo Telegram ID."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("DELETE FROM admins WHERE telegram_id = ?", (telegram_id,))
        await db.commit()


async def is_admin(telegram_id: int) -> bool:
    """Verifica se um usuário é administrador."""
    if telegram_id in config.get_admin_ids():
        return True

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT 1 FROM admins WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row is not None


# ========== Operações de transações ==========

async def create_transaction(telegram_id: int, plan_id: int, amount_brl: float,
                             provider_transaction_id: str, qr_code: str, copy_paste_code: str,
                             provider_payload: Dict[str, Any]) -> int:
    """Cria uma nova transação pendente."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO transactions (
                telegram_id, plan_id, provider_transaction_id, amount_brl,
                status, qr_code, copy_paste_code, provider_payload,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, 'pending', ?, ?, ?, ?, ?)
        """, (telegram_id, plan_id, provider_transaction_id, amount_brl,
              qr_code, copy_paste_code, json.dumps(provider_payload), now, now))
        await db.commit()
        return cursor.lastrowid


async def get_transaction_by_provider_id(provider_transaction_id: str) -> Optional[Dict[str, Any]]:
    """Busca uma transação pelo ID do provedor."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT * FROM transactions WHERE provider_transaction_id = ?",
            (provider_transaction_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None


async def update_transaction_status(provider_transaction_id: str, status: str,
                                    delivery_payload: Optional[Dict] = None) -> bool:
    """Atualiza o status de uma transação."""
    now = datetime.utcnow().isoformat()
    params = [status, now]

    query = "UPDATE transactions SET status = ?, updated_at = ?"

    if status == "paid":
        query += ", paid_at = ?"
        params.append(now)

    if delivery_payload is not None:
        query += ", delivery_payload = ?"
        params.append(json.dumps(delivery_payload))

    query += " WHERE provider_transaction_id = ?"
    params.append(provider_transaction_id)

    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute(query, params)
        await db.commit()
        return cursor.rowcount > 0


async def mark_transaction_paid(provider_transaction_id: str) -> bool:
    """Marca uma transação como paga."""
    return await update_transaction_status(provider_transaction_id, "paid")


async def mark_transaction_delivered(provider_transaction_id: str, delivery_payload: Dict[str, Any]) -> bool:
    """Marca uma transação como entregue."""
    return await update_transaction_status(provider_transaction_id, "delivered", delivery_payload)


# ========== Estoque de Fotos (abastecimento) ==========

async def add_abastecimento(plan_id: int, foto_file_id: str, quantidade: int, admin_id: int) -> int:
    """Registra um abastecimento: salva a foto e a quantidade disponível para um plano."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO estoque_fotos (plan_id, foto_file_id, quantidade, usado, admin_id, created_at)
            VALUES (?, ?, ?, 0, ?, ?)
        """, (plan_id, foto_file_id, quantidade, admin_id, now))
        await db.commit()
        return cursor.lastrowid


async def get_next_estoque_foto(plan_id: int) -> Optional[str]:
    """
    Retorna o file_id da próxima foto disponível no estoque do plano (FIFO).
    Marca o registro como usado após retirar. Retorna None se estoque vazio.
    """
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT id, foto_file_id, quantidade, usado
            FROM estoque_fotos
            WHERE plan_id = ? AND usado < quantidade
            ORDER BY created_at ASC
            LIMIT 1
        """, (plan_id,)) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        foto_file_id = row["foto_file_id"]
        novo_usado   = row["usado"] + 1

        await db.execute(
            "UPDATE estoque_fotos SET usado = ? WHERE id = ?",
            (novo_usado, row["id"]),
        )
        await db.commit()
        return foto_file_id


async def get_estoque(plan_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Retorna o estoque disponível. Se plan_id informado, retorna só aquele plano."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if plan_id:
            async with db.execute("""
                SELECT p.id as plan_id, p.name as plan_name,
                       COALESCE(SUM(ef.quantidade - ef.usado), 0) as disponivel
                FROM plans p
                LEFT JOIN estoque_fotos ef ON ef.plan_id = p.id
                WHERE p.id = ?
                GROUP BY p.id
            """, (plan_id,)) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute("""
                SELECT p.id as plan_id, p.name as plan_name,
                       COALESCE(SUM(ef.quantidade - ef.usado), 0) as disponivel
                FROM plans p
                LEFT JOIN estoque_fotos ef ON ef.plan_id = p.id
                WHERE p.is_active = 1
                GROUP BY p.id
                ORDER BY p.price_brl ASC
            """) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def list_abastecimentos(plan_id: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
    """Lista os últimos abastecimentos registrados."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        if plan_id:
            async with db.execute("""
                SELECT ef.*, p.name as plan_name
                FROM estoque_fotos ef
                JOIN plans p ON ef.plan_id = p.id
                WHERE ef.plan_id = ?
                ORDER BY ef.created_at DESC
                LIMIT ?
            """, (plan_id, limit)) as cursor:
                rows = await cursor.fetchall()
        else:
            async with db.execute("""
                SELECT ef.*, p.name as plan_name
                FROM estoque_fotos ef
                JOIN plans p ON ef.plan_id = p.id
                ORDER BY ef.created_at DESC
                LIMIT ?
            """, (limit,)) as cursor:
                rows = await cursor.fetchall()
        return [dict(row) for row in rows]


async def list_all_users() -> List[Dict[str, Any]]:
    """Lista todos os usuários cadastrados (para broadcast)."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT telegram_id FROM users") as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


# ========== Saldo de Usuários ==========

async def get_user_balance(telegram_id: int) -> float:
    """Retorna o saldo atual de um usuário. Retorna 0.0 se não existir registro."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT balance FROM user_balances WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0.0


async def add_user_balance(telegram_id: int, valor: float) -> float:
    """
    Adiciona valor ao saldo do usuário.
    Cria o registro se não existir.
    Retorna o novo saldo.
    """
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO user_balances (telegram_id, balance, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                balance = balance + excluded.balance,
                updated_at = excluded.updated_at
        """, (telegram_id, valor, now))
        await db.commit()

        async with db.execute(
            "SELECT balance FROM user_balances WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0.0


async def remove_user_balance(telegram_id: int, valor: float) -> float:
    """
    Retira valor do saldo do usuário.
    Lança ValueError se saldo insuficiente.
    Retorna o novo saldo.
    """
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT balance FROM user_balances WHERE telegram_id = ?", (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            saldo_atual = row[0] if row else 0.0

        if saldo_atual < valor:
            raise ValueError(
                f"Saldo insuficiente. Atual: R$ {saldo_atual:.2f} | Solicitado: R$ {valor:.2f}"
            )

        novo_saldo = saldo_atual - valor
        await db.execute("""
            INSERT INTO user_balances (telegram_id, balance, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                balance = ?,
                updated_at = excluded.updated_at
        """, (telegram_id, novo_saldo, now, novo_saldo))
        await db.commit()
        return novo_saldo


# ========== Configurações / Gateway ==========

async def get_setting(key: str) -> Optional[str]:
    """Retorna o valor de uma configuração salva no banco."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        ) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None


async def set_setting(key: str, value: str):
    """Salva ou atualiza uma configuração no banco."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute("""
            INSERT INTO settings (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (key, value, now))
        await db.commit()


async def get_pusshipay_token() -> Optional[str]:
    """Retorna o token da Pusshipay salvo no banco. Fallback para config.py se não houver."""
    token = await get_setting("pusshipay_token")
    if not token:
        # Fallback para a variável de ambiente/config original
        return getattr(config, "PUSHSHIPAY_API_TOKEN", None)
    return token


async def set_pusshipay_token(token: str):
    """Salva o novo token da Pusshipay no banco."""
    await set_setting("pusshipay_token", token)


# ========== Contas de Streaming ==========

async def add_conta_streaming(servico: str, preco_brl: float, email: str, senha: str, admin_id: int) -> int:
    """Cadastra uma nova conta de streaming no estoque."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        cursor = await db.execute("""
            INSERT INTO contas_streaming (servico, preco_brl, email, senha, usado, admin_id, created_at)
            VALUES (?, ?, ?, ?, 0, ?, ?)
        """, (servico, preco_brl, email, senha, admin_id, now))
        await db.commit()
        return cursor.lastrowid


async def list_servicos_streaming() -> List[Dict[str, Any]]:
    """Lista os serviços disponíveis com quantidade em estoque."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT servico,
                   MIN(preco_brl) as preco_brl,
                   COUNT(*) FILTER (WHERE usado = 0) as disponivel,
                   COUNT(*) as total
            FROM contas_streaming
            GROUP BY servico
            ORDER BY servico ASC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_next_conta_streaming(servico: str) -> Optional[Dict[str, Any]]:
    """Retorna a próxima conta disponível para um serviço (FIFO). Marca como usado."""
    now = datetime.utcnow().isoformat()
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT * FROM contas_streaming
            WHERE servico = ? AND usado = 0
            ORDER BY id ASC
            LIMIT 1
        """, (servico,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                return None
            conta = dict(row)

        await db.execute(
            "UPDATE contas_streaming SET usado = 1, vendido_at = ? WHERE id = ?",
            (now, conta["id"])
        )
        await db.commit()
        return conta


async def set_comprador_streaming(conta_id: int, telegram_id: int):
    """Registra quem comprou a conta."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        await db.execute(
            "UPDATE contas_streaming SET telegram_id_comprador = ? WHERE id = ?",
            (telegram_id, conta_id)
        )
        await db.commit()


async def get_estoque_streaming() -> List[Dict[str, Any]]:
    """Retorna estoque completo de streaming por serviço."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("""
            SELECT servico,
                   MIN(preco_brl) as preco_brl,
                   COUNT(*) FILTER (WHERE usado = 0) as disponivel,
                   COUNT(*) as total
            FROM contas_streaming
            GROUP BY servico
            ORDER BY servico ASC
        """) as cursor:
            rows = await cursor.fetchall()
            return [dict(row) for row in rows]


async def get_preco_streaming(servico: str) -> Optional[float]:
    """Retorna o preço da próxima conta disponível de um serviço."""
    async with aiosqlite.connect(config.DATABASE_PATH) as db:
        async with db.execute("""
            SELECT preco_brl FROM contas_streaming
            WHERE servico = ? AND usado = 0
            ORDER BY id ASC LIMIT 1
        """, (servico,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else None
