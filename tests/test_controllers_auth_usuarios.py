from unittest.mock import patch
from app import create_app


def test_rota_protegida_redireciona_para_login():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]


def test_login_valido_cria_sessao():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()

    with patch(
        "controllers.auth_controller.Usuario.autenticar",
        return_value={
            "id": 1,
            "nome": "Admin",
            "email": "admin@pense.com",
            "funcao_id": 1,
            "funcao": "Admin",
        },
    ):
        resp = client.post(
            "/login",
            data={"email": "admin@pense.com", "senha": "123"},
            follow_redirects=False,
        )

    assert resp.status_code == 302
    with client.session_transaction() as sess:
        assert sess["usuario_id"] == 1
        assert sess["usuario_funcao"] == "Admin"


def test_usuario_normal_bloqueado_em_gestao_usuarios():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Visitante"
        sess["usuario_funcao"] = "normal"

    resp = client.get("/usuarios")
    assert resp.status_code == 403


def test_admin_pode_promover_usuario_normal():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 1
        sess["usuario_nome"] = "Admin"
        sess["usuario_funcao"] = "Admin"

    with patch(
        "controllers.usuario_controller.Usuario.atualizar_funcao", return_value=True
    ) as mock_update:
        resp = client.post("/usuarios/2/promover", follow_redirects=False)

    assert resp.status_code == 302
    mock_update.assert_called_once_with(2, "Admin")
