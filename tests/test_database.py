from unittest.mock import MagicMock, patch
import database


def test_init_db_executes_schema_and_seed():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = None

    with patch("database.get_connection", return_value=mock_conn):
        database.init_db()

    executed_sql = " ".join(call.args[0] for call in mock_cur.execute.call_args_list)
    assert "CREATE TABLE IF NOT EXISTS funcoes" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS usuarios" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS modalidades_formularios" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS autores" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS instituicoes" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS formularios" in executed_sql
    assert mock_conn.commit.called


def test_get_connection_closes_connection_on_context_exit():
    raw_conn = MagicMock()
    with patch("database.psycopg2.connect", return_value=raw_conn):
        with database.get_connection() as conn:
            assert conn is raw_conn

    assert raw_conn.close.called
