import sqlite3
from pathlib import Path
import asyncio
from sqlalchemy import text  # <-- ADICIONE ESTA LINHA AQUI
from src.db.session import engine

def run_migration():
    # Caminho exato onde seu banco está
    db_path = Path("data/jobscout.db")
    
    if not db_path.exists():
        print(f"Erro: Banco de dados não encontrado em {db_path}")
        return

    print(f"Conectando ao banco SQLite: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Comandos SQL para adicionar apenas as novas colunas
    novas_colunas = [
        "ALTER TABLE jobs ADD COLUMN salary_expectation VARCHAR(255);"
    ]

    for query in novas_colunas:
        try:
            cursor.execute(query)
            print(f"Sucesso: Coluna adicionada -> {query}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Aviso ignorado: A coluna já existe -> {query}")
            else:
                print(f"Erro inesperado na query {query}: {e}")

    conn.commit()
    conn.close()
    print("\nMigração das colunas concluída com sucesso! Seus dados antigos estão seguros e a base está pronta para a IA.")

# No seu ficheiro de migração
async def add_sector_column():
    async with engine.begin() as conn:
        try:
            # Comando específico do SQLite para adicionar coluna
            await conn.execute(text("ALTER TABLE jobs ADD COLUMN sector VARCHAR(100);"))
            print("✅ Coluna 'sector' adicionada com sucesso.")
        except Exception as e:
            if "duplicate column name" in str(e).lower():
                print("ℹ️ Coluna 'sector' já existe.")
            else:
                print(f"❌ Erro ao adicionar coluna: {e}")

if __name__ == "__main__":
    # O asyncio.run() cria o loop de eventos necessário para executar a função async
    asyncio.run(add_sector_column())

