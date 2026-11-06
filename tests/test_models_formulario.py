import pytest
from unittest.mock import MagicMock, patch
from models.formulario import Formulario


def test_formulario_criar_executa_transacao_unica_e_salva_na_tabela_arquivos():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    # autor lookup (None), autor insert (10), inst lookup (None), inst insert (20), arquivo insert (88), form insert (30)
    mock_cur.fetchone.side_effect = [None, (10,), None, (20,), (88,), (30,)]

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
            nome_arquivo="artigo.pdf",
            usuario_id=7,
        )

    assert novo_id == 30
    executed_sql = " ".join(c.args[0] for c in mock_cur.execute.call_args_list)
    assert "INSERT INTO arquivos" in executed_sql
    assert "usuario_id" in executed_sql
    assert "arquivo_id" in executed_sql
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
    assert "arquivo_id =" not in update_queries[0]


def test_formulario_listar_todos_inclui_usuario_foto_id():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchall.return_value = [
        (
            1,
            "Título",
            "Resumo",
            "ia",
            "Computação",
            1,
            "Pesquisa",
            10,
            "Ana",
            "ana@ifrs.edu.br",
            "IA",
            "Farroupilha",
            20,
            "IFRS",
            "Farroupilha",
            7,
            99,
            88,
        )
    ]

    with patch("models.formulario.get_connection", return_value=mock_conn):
        lista = Formulario.listar_todos()

    assert len(lista) == 1
    assert lista[0]["usuario_id"] == 7
    assert lista[0]["usuario_foto_id"] == 99
    assert lista[0]["arquivo_id"] == 88
