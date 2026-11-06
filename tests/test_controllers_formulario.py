import io
from unittest.mock import patch
from app import create_app


def test_download_pdf_retorna_bytes_do_banco():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Normal"
        sess["usuario_funcao"] = "normal"

    with patch(
        "controllers.formulario_controller.Formulario.buscar_arquivo",
        return_value=(b"%PDF-1.4 test", "Teoria Quantica"),
    ):
        resp = client.get("/trabalho/1/arquivo")

    assert resp.status_code == 200
    assert resp.mimetype == "application/pdf"
    assert resp.data == b"%PDF-1.4 test"


def test_usuario_normal_nao_pode_excluir_formulario():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Normal"
        sess["usuario_funcao"] = "normal"

    resp = client.post("/trabalho/1/excluir")
    assert resp.status_code == 403


def test_admin_pode_excluir_formulario():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 1
        sess["usuario_nome"] = "Admin"
        sess["usuario_funcao"] = "Admin"

    with patch(
        "controllers.formulario_controller.Formulario.excluir", return_value=True
    ) as mock_del:
        resp = client.post("/trabalho/1/excluir", follow_redirects=False)

    assert resp.status_code == 302
    mock_del.assert_called_once_with(1)


def test_submissao_rejeita_arquivo_nao_pdf():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Normal"
        sess["usuario_funcao"] = "normal"

    with patch(
        "controllers.formulario_controller.Modalidade.listar_todas",
        return_value=[{"id": 1, "descricao": "Pesquisa"}],
    ), patch(
        "controllers.formulario_controller.Modalidade.buscar_por_id",
        return_value={"id": 1, "descricao": "Pesquisa"},
    ):
        resp = client.post(
            "/formulario",
            data={
                "autor_nome": "Ana",
                "autor_email": "ana@ifrs.edu.br",
                "autor_area": "Física",
                "autor_cidade": "Farroupilha",
                "instituicao_nome": "IFRS",
                "instituicao_cidade": "Farroupilha",
                "titulo": "Teoria Quântica",
                "palavra_chave": "física, quântica",
                "area_conhecimento": "Ciências Exatas",
                "modalidade_id": "1",
                "resumo": "Resumo do trabalho",
                "arquivo": (io.BytesIO(b"nao eh pdf"), "arquivo.txt"),
            },
            content_type="multipart/form-data",
        )
    assert resp.status_code == 400


def test_submissao_erro_preserva_campos_autor_e_instituicao():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Normal"
        sess["usuario_funcao"] = "normal"

    with patch(
        "controllers.formulario_controller.Modalidade.listar_todas",
        return_value=[{"id": 1, "descricao": "Pesquisa"}],
    ), patch(
        "controllers.formulario_controller.Modalidade.buscar_por_id",
        return_value={"id": 1, "descricao": "Pesquisa"},
    ):
        resp = client.post(
            "/formulario",
            data={
                "autor_nome": "Maria Silva",
                "autor_email": "maria@ifrs.edu.br",
                "autor_area": "Biologia",
                "autor_cidade": "Bento Gonçalves",
                "instituicao_nome": "IFRS - Campus Bento",
                "instituicao_cidade": "Bento Gonçalves",
                "titulo": "Título válido",
                "palavra_chave": "bio",
                "area_conhecimento": "Ciências Biológicas",
                "modalidade_id": "1",
                "resumo": "Resumo...",
                "arquivo": (io.BytesIO(b"invalido"), "notas.txt"),
            },
            content_type="multipart/form-data",
        )

    html = resp.get_data(as_text=True)
    assert resp.status_code == 400
    assert "Maria Silva" in html
    assert "IFRS - Campus Bento" in html


def test_botao_sair_nao_exibe_nome_do_usuario_e_cards_usam_foto_do_usuario():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Fulano da Silva"
        sess["usuario_funcao"] = "normal"
        sess["usuario_foto_id"] = 45

    with patch(
        "controllers.formulario_controller.Formulario.listar_todos",
        return_value=[
            {
                "id": 10,
                "titulo": "Trabalho com Foto",
                "resumo": "Resumo teste",
                "palavra_chave": "ia",
                "area_conhecimento": "Computação",
                "modalidade_id": 1,
                "modalidade": "Pesquisa",
                "autor_id": 1,
                "autor_nome": "Fulano da Silva",
                "autor_email": "fulano@ifrs.edu.br",
                "autor_area": "TI",
                "autor_cidade": "Farroupilha",
                "instituicao_id": 1,
                "instituicao_nome": "IFRS",
                "instituicao_cidade": "Farroupilha",
                "usuario_id": 2,
                "usuario_foto_id": 45,
                "arquivo_id": 88,
            }
        ],
    ):
        resp = client.get("/")

    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert "SAIR (Fulano da Silva)" not in html
    assert ">SAIR<" in html
    assert "/arquivos/45" in html


def test_formulario_renderiza_wizard_de_tres_etapas():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Normal"
        sess["usuario_funcao"] = "normal"

    with patch(
        "controllers.formulario_controller.Modalidade.listar_todas",
        return_value=[{"id": 1, "descricao": "Pesquisa"}],
    ):
        resp = client.get("/formulario")

    html = resp.get_data(as_text=True)
    assert resp.status_code == 200
    assert 'data-step="1"' in html
    assert 'data-step="2"' in html
    assert 'data-step="3"' in html
    assert 'id="btn-proximo"' in html
    assert 'id="btn-voltar"' in html
