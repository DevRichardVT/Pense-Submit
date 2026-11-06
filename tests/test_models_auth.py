import pytest
from unittest.mock import MagicMock, patch
from models.usuario import Usuario
from models.modalidade import Modalidade
from models.funcao import Funcao


def test_usuario_criar_rejeita_senha_maior_que_20_chars():
    with pytest.raises(ValueError, match="20 caracteres"):
        Usuario.criar("Teste", "teste@ifrs.edu.br", "a" * 21)


def test_usuario_criar_rejeita_email_duplicado():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = (99,)

    with patch("models.usuario.get_connection", return_value=mock_conn):
        with pytest.raises(ValueError, match="E-mail já cadastrado"):
            Usuario.criar("Teste", "dup@ifrs.edu.br", "123456")


def test_usuario_criar_com_foto_salva_arquivo_e_vincula():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.side_effect = [None, (2,), (77,), (5,)]

    with patch("models.usuario.get_connection", return_value=mock_conn):
        user_id = Usuario.criar(
            "Maria",
            "maria@ifrs.edu.br",
            "123456",
            foto=("perfil.png", "image/png", b"\x89PNG..."),
        )

    assert user_id == 5
    executed_sql = " ".join(c.args[0] for c in mock_cur.execute.call_args_list)
    assert "INSERT INTO arquivos" in executed_sql
    assert "foto_arquivo_id" in executed_sql
    assert mock_conn.commit.called


def test_usuario_autenticar_retorna_dados_com_funcao_e_foto():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = (1, "Admin User", "admin@pense.com", 1, "Admin", 77)

    with patch("models.usuario.get_connection", return_value=mock_conn):
        user = Usuario.autenticar("admin@pense.com", "admin123")

    assert user == {
        "id": 1,
        "nome": "Admin User",
        "email": "admin@pense.com",
        "funcao_id": 1,
        "funcao": "Admin",
        "foto_arquivo_id": 77,
    }


def test_usuario_atualizar_funcao():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = (1,)
    mock_cur.rowcount = 1

    with patch("models.usuario.get_connection", return_value=mock_conn):
        ok = Usuario.atualizar_funcao(2, "Admin")

    assert ok is True
    assert mock_conn.commit.called
