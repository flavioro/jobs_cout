from __future__ import annotations

import sqlite3
from pathlib import Path

DB_PATH = Path("data/jobscout.db")


def _column_exists(cursor: sqlite3.Cursor, table_name: str, column_name: str) -> bool:
    cursor.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _add_column_if_missing(cursor: sqlite3.Cursor, table_name: str, column_name: str, definition: str) -> None:
    if _column_exists(cursor, table_name, column_name):
        print(f"Coluna ja existe: {table_name}.{column_name}")
        return
    cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN {column_name} {definition};")
    print(f"Coluna adicionada: {table_name}.{column_name}")


def _create_job_candidates_table(cursor: sqlite3.Cursor) -> None:
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS job_candidates (
            id VARCHAR(36) NOT NULL PRIMARY KEY,
            source VARCHAR(50) NOT NULL DEFAULT 'linkedin',
            source_job_id VARCHAR(255),
            source_url VARCHAR(2048) NOT NULL,
            canonical_source_url VARCHAR(2048) NOT NULL,
            source_search_url VARCHAR(2048),
            title VARCHAR(512),
            company VARCHAR(255),
            location_raw VARCHAR(255),
            workplace_type VARCHAR(50),
            employment_type_raw VARCHAR(100),
            seniority_hint VARCHAR(100),
            is_easy_apply BOOLEAN,
            availability_status VARCHAR(50),
            availability_reason VARCHAR(100),
            extraction_status VARCHAR(50),
            missing_fields JSON,
            detail_completed BOOLEAN NOT NULL DEFAULT 0,
            detail_url_opened BOOLEAN NOT NULL DEFAULT 0,
            detail_completion_source VARCHAR(100),
            detail_error TEXT,
            raw_card_text TEXT,
            raw_detail_text TEXT,
            raw_payload_json JSON,
            processing_status VARCHAR(50) NOT NULL DEFAULT 'pending',
            processing_attempts INTEGER NOT NULL DEFAULT 0,
            processing_error TEXT,
            job_id VARCHAR(36),
            processed_at DATETIME,
            collected_at DATETIME NOT NULL,
            created_at DATETIME,
            updated_at DATETIME,
            FOREIGN KEY(job_id) REFERENCES jobs (id) ON DELETE SET NULL,
            CONSTRAINT uq_job_candidates_source_job_id UNIQUE (source, source_job_id),
            CONSTRAINT uq_job_candidates_source_url UNIQUE (source, canonical_source_url)
        );
    """)
    print("Tabela garantida: job_candidates")
    for query in [
        "CREATE INDEX IF NOT EXISTS ix_job_candidates_source ON job_candidates (source);",
        "CREATE INDEX IF NOT EXISTS ix_job_candidates_source_job_id ON job_candidates (source_job_id);",
        "CREATE INDEX IF NOT EXISTS ix_job_candidates_canonical_source_url ON job_candidates (canonical_source_url);",
        "CREATE INDEX IF NOT EXISTS ix_job_candidates_availability_status ON job_candidates (availability_status);",
        "CREATE INDEX IF NOT EXISTS ix_job_candidates_extraction_status ON job_candidates (extraction_status);",
        "CREATE INDEX IF NOT EXISTS ix_job_candidates_processing_status ON job_candidates (processing_status);",
        "CREATE INDEX IF NOT EXISTS ix_job_candidates_job_id ON job_candidates (job_id);",
        "CREATE INDEX IF NOT EXISTS ix_job_candidates_source_status ON job_candidates (source, processing_status);",
        "CREATE INDEX IF NOT EXISTS ix_job_candidates_source_collected ON job_candidates (source, collected_at);",
    ]:
        cursor.execute(query)
    print("Indices garantidos para job_candidates")


def run_migration() -> None:
    if not DB_PATH.exists():
        print(f"Erro: Banco de dados nao encontrado em {DB_PATH}")
        return
    print(f"Conectando ao banco SQLite: {DB_PATH}")
    conn = sqlite3.connect(DB_PATH)
    try:
        cursor = conn.cursor()
        _add_column_if_missing(cursor, "jobs", "salary_expectation", "VARCHAR(255)")
        _add_column_if_missing(cursor, "jobs", "sector", "VARCHAR(100)")
        _create_job_candidates_table(cursor)
        conn.commit()
        print("\nMigracao concluida com sucesso.")
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
