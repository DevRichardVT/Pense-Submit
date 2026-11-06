import pytest
from unittest.mock import MagicMock, patch
from models.formulario import Formulario


def test_formulario_criar_executa_transacao_unica():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.side_effect = [None, (10,), None, (20,), (30,)]

    with patch("models.formulario.get_connection", return_value=mock_conn):
        novo_id = Formulario.criar(
            dados_autor={
                "nome": "Ana",
                "email": "ana@ifrs.edu.br",
                "area": "IA",
                "cidade": "Farroupilha",
            },
            dados_instituicao={"nome": "IFRS", "cidade": "Farroupilha"},
            dados_form={
                "modalidade_id": 1,
                "titulo": "Título Curto",
                "resumo": "Resumo...",
                "palavra_chave": "ia, python",
                "area_conhecimento": "Computação",
            },
            arquivo_bytes=b"%PDF-1.4...",
        )

    assert novo_id == 30
    assert mock_conn.commit.called


def test_formulario_criar_rejeita_titulo_maior_que_50_chars():
    with pytest.raises(ValueError, match="50 caracteres"):
        Formulario.criar(
            dados_autor={
                "nome": "Ana",
                "email": "ana@ifrs.edu.br",
                "area": "IA",
                "cidade": "Farroupilha",
            },
            dados_instituicao={"nome": "IFRS", "cidade": "Farroupilha"},
            dados_form={
                "modalidade_id": 1,
                "titulo": "T" * 51,
                "resumo": "Resumo...",
                "palavra_chave": "ia",
                "area_conhecimento": "Computação",
            },
            arquivo_bytes=b"%PDF-1.4...",
        )


def test_formulario_atualizar_sem_novo_pdf_mantem_arquivo_existente():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.side_effect = [None, (10,), None, (20,)]
    mock_cur.rowcount = 1

    with patch("models.formulario.get_connection", return_value=mock_conn):
        ok = Formulario.atualizar(
            form_id=5,
            dados_autor={
                "nome": "Ana",
                "email": "ana@ifrs.edu.br",
                "area": "IA",
                "cidade": "Farroupilha",
            },
            dados_instituicao={"nome": "IFRS", "cidade": "Farroupilha"},
            dados_form={
                "modalidade_id": 2,
                "titulo": "Título Editado",
                "resumo": "Novo resumo",
                "palavra_chave": "ia",
                "area_conhecimento": "Computação",
            },
            arquivo_bytes=None,
        )

    assert ok is True
    update_queries = [
        c.args[0]
        for c in mock_cur.execute.call_args_list
        if "UPDATE formularios" in c.args[0]
    ]
    assert len(update_queries) == 1
    assert "arquivo =" not in update_queries[0]
