import pytest
from unittest.mock import AsyncMock, MagicMock
from datetime import datetime, timezone
from src.services.persistence_service import upsert_job
from src.schemas.jobs import JobRecordSchema
from src.core.enums import JobSource, JobStatus

@pytest.mark.asyncio
async def test_upsert_job_blocks_missing_required_fields():
    """Garante que vagas sem título, empresa ou descrição não entram no banco."""
    mock_session = AsyncMock()
    
    # Caso 1: Sem título
    bad_record = MagicMock(spec=JobRecordSchema)
    bad_record.url = "http://fake"
    bad_record.title = "" # Vazio
    bad_record.company = "Tech"
    bad_record.description_text = "Texto"
    
    result = await upsert_job(mock_session, bad_record)
    assert result is None
    mock_session.add.assert_not_called()

    # Caso 2: Sem descrição
    bad_record.title = "Dev"
    bad_record.description_text = None # Nulo
    
    result = await upsert_job(mock_session, bad_record)
    assert result is None
    mock_session.add.assert_not_called()

@pytest.mark.asyncio
async def test_upsert_job_deduplicates_by_canonical_url_only():
    """Valida que o sistema atualiza a vaga existente se a URL bater, ignorando o fingerprint."""
    mock_session = AsyncMock()
    
    # 1. Preparamos o registro que chega (com novo fingerprint)
    new_record = MagicMock()
    new_record.external_id = "123"
    new_record.url = "http://fake"
    new_record.canonical_url = "http://linkedin.com/vaga-1"
    new_record.fingerprint = "NOVO_FINGERPRINT"
    new_record.title = "Python Dev Senior"
    new_record.company = "Google"
    new_record.description_text = "Nova descrição editada"
    new_record.source = JobSource.LINKEDIN
    new_record.status = JobStatus.SUCCESS
    new_record.related_jobs = []

    # ADICIONE ESTA LINHA: Ensina o mock a simular o comportamento do Pydantic
    new_record.model_dump.return_value = {"title": "Python Dev Senior", "fingerprint": "NOVO_FINGERPRINT"}

    # 2. Simulamos que já existe uma vaga no banco com a MESMA URL
    existing_job = MagicMock()
    existing_job.id = "uuid-original"
    existing_job.canonical_url = "http://linkedin.com/vaga-1"
    existing_job.fingerprint = "FINGERPRINT_ANTIGO"
    
    # Mock do retorno da query (scalar_one_or_none)
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = existing_job
    mock_session.execute.return_value = mock_result

    # 3. Executamos
    result = await upsert_job(mock_session, new_record)

    # 4. Asserções
    assert result.id == "uuid-original"
    # Verificamos se o título foi atualizado para o novo valor
    assert existing_job.title == "Python Dev Senior"
    # Verificamos se o fingerprint mudou (provando que a atualização ocorreu)
    assert existing_job.fingerprint == "NOVO_FINGERPRINT"
    # Garante que NÃO chamou o add (inserção), apenas commit (atualização)
    mock_session.add.assert_not_called()
    mock_session.commit.assert_called()