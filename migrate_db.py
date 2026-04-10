import sqlite3
from pathlib import Path

def run_migration():
    # Caminho exato onde seu banco está configurado para ficar
    db_path = Path("data/jobscout.db")
    
    if not db_path.exists():
        print(f"Erro: Banco de dados não encontrado em {db_path}")
        return

    print(f"Conectando ao banco SQLite: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Comandos SQL para adicionar apenas as novas colunas
    novas_colunas = [
        "ALTER TABLE jobs ADD COLUMN salary_raw VARCHAR(255);",
        "ALTER TABLE jobs ADD COLUMN skills JSON;",
        "ALTER TABLE jobs ADD COLUMN fit_score INTEGER;",
        "ALTER TABLE jobs ADD COLUMN fit_rationale TEXT;",
        "ALTER TABLE jobs ADD COLUMN applied_at DATETIME;",
        "ALTER TABLE jobs ADD COLUMN notes TEXT;",
        "ALTER TABLE jobs ADD COLUMN template_source VARCHAR(100);"
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
    print("\nMigração das colunas concluída com sucesso! Seus dados estão a salvo.")

if __name__ == "__main__":
    run_migration()