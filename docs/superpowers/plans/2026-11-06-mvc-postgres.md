# MVC & PostgreSQL Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrar o PEnsE-Submite de uma lista em memória para a arquitetura MVC com PostgreSQL (SQL puro), autenticação obrigatória, gestão de permissões (`Admin` e `normal`) e CRUD completo de formulários com upload de PDF em `BYTEA`.

**Architecture:** Aplicação Flask estruturada em MVC modular com `database.py` (conexão `psycopg2` e seed idempotente), camada `models/` com SQL parametrizado puro para as 6 tabelas do schema, camada `controllers/` dividida em Blueprints (`auth`, `usuario`, `formulario`) protegidos por decorators de sessão, e `templates/` Jinja2 mantendo a identidade visual existente.

**Tech Stack:** Python 3.12+, Flask 3.1.3, PostgreSQL (`psycopg2-binary`), `python-dotenv`, `pytest`.

**Spec:** `docs/superpowers/specs/2026-11-06-mvc-postgres-design.md`

## Global Constraints

- Respeitar estritamente as 6 tabelas e limites de coluna do schema PostgreSQL:
  - `funcoes`: `id SERIAL PRIMARY KEY`, `descricao VARCHAR(255) NOT NULL` (`'Admin'`, `'normal'`)
  - `usuarios`: `id SERIAL PRIMARY KEY`, `funcao_id INTEGER NOT NULL REFERENCES funcoes(id)`, `nome VARCHAR(100) NOT NULL`, `email VARCHAR(100) NOT NULL`, `senha VARCHAR(20) NOT NULL`
  - `modalidades_formularios`: `id SERIAL PRIMARY KEY`, `descricao VARCHAR(20) NOT NULL` (`'Ensino'`, `'Pesquisa'`, `'Extensão'`)
  - `autores`: `id SERIAL PRIMARY KEY`, `nome VARCHAR(100) NOT NULL`, `email VARCHAR(100) NOT NULL`, `area VARCHAR(100) NOT NULL`, `cidade VARCHAR(100) NOT NULL`
  - `instituicoes`: `id SERIAL PRIMARY KEY`, `nome VARCHAR(255) NOT NULL`, `cidade VARCHAR(100) NOT NULL`
  - `formularios`: `id SERIAL PRIMARY KEY`, `autor_id INTEGER NOT NULL REFERENCES autores(id)`, `modalidade_id INTEGER NOT NULL REFERENCES modalidades_formularios(id)`, `instituicao_id INTEGER NOT NULL REFERENCES instituicoes(id)`, `titulo VARCHAR(50) NOT NULL`, `resumo TEXT NOT NULL`, `arquivo BYTEA NOT NULL`, `palavra_chave VARCHAR(100) NOT NULL`, `area_conhecimento VARCHAR(255) NOT NULL`
- Proibido usar ORM (SQLAlchemy); todas as queries devem usar SQL puro parametrizado (`%s`).
- Nenhum PDF deve ser salvo em disco (`static/uploads`); o binário vai para `formularios.arquivo` (`BYTEA`).
- Todas as rotas da aplicação (inclusive `/`) exigem login, exceto `/login`, `/cadastro` e arquivos estáticos.

## Review Focus

1. **Cadastro com e-mail duplicado ou senha > 20 caracteres:** O sistema deve rejeitar com mensagem amigável antes de estourar erro no PostgreSQL (`VARCHAR(20)`).
2. **Edição de formulário pelo Admin sem enviar novo PDF:** O sistema deve preservar os bytes `BYTEA` já armazenados na coluna `arquivo` em vez de sobrescrever com vazio/nulo.
3. **Submissão de formulário com título > 50 caracteres ou arquivo que não seja PDF:** Deve retornar HTTP 400 com `flash` explicativo sem gravar registros órfãos em `autores` ou `instituicoes`.
4. **Acesso de usuário `normal` a rotas exclusivas de `Admin` (`/usuarios`, `/trabalho/<id>/editar`, `/trabalho/<id>/excluir`):** Deve bloquear com HTTP 403 ou redirecionar com aviso de permissão negada.
5. **Leitura de `BYTEA` do `psycopg2` (`memoryview` / `bytes`) no download do PDF:** `send_file` deve converter `bytes(arquivo)` para `io.BytesIO` com `mimetype="application/pdf"`.

---

### Task 1: Configuração do Banco PostgreSQL, DDL e Seed Inicial (`database.py`)

**Files:**
- Modify: `requirements.txt`
- Create: `.env.example`
- Create: `database.py`
- Test: `tests/test_database.py`

**Interfaces:**
- Consumes: Variáveis de ambiente `DATABASE_URL` (ou `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`), `ADMIN_NOME`, `ADMIN_EMAIL`, `ADMIN_SENHA`.
- Produces:
  - `database.get_connection() -> psycopg2.extensions.connection`
  - `database.init_db() -> None` (cria as 6 tabelas se não existirem e executa seed idempotente de `funcoes`, `modalidades_formularios` e usuário `Admin` padrão)

- [ ] **Step 1: Atualizar `requirements.txt` e instalar dependências no `.venv`**

Adicionar `psycopg2-binary>=2.9.9`, `python-dotenv>=1.0.1` e `pytest>=8.0.0` ao `requirements.txt` e instalar via `.\.venv\Scripts\pip.exe install -r requirements.txt`.

- [ ] **Step 2: Escrever o teste de inicialização e seed em `tests/test_database.py`**

```python
from unittest.mock import MagicMock, patch
import database

def test_init_db_executes_schema_and_seed():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    # Simula retorno de ids para funcoes, modalidades e checagem de admin
    mock_cur.fetchone.side_effect = [(1,), (2,), None]

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
```

- [ ] **Step 3: Rodar o teste para verificar que falha**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_database.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'database'`)

- [ ] **Step 4: Implementar `database.py` e `.env.example`**

Implementar `get_connection()` lendo `DATABASE_URL` ou parâmetros `DB_*` com `dotenv`, e `init_db()` criando as 6 tabelas com as constraints exatas do schema e inserindo de forma idempotente as funções `('Admin', 'normal')`, modalidades `('Ensino', 'Pesquisa', 'Extensão')` e o usuário `Admin` chumbado (`admin@pense.com` / `admin123`, configurável via `.env`).

- [ ] **Step 5: Rodar o teste para verificar que passa**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_database.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```powershell
git add requirements.txt .env.example database.py tests/test_database.py
git commit -m "feat(db): add PostgreSQL connection, DDL schema and initial seed"
```

---

### Task 2: Models de Autenticação e Domínio (`Funcao`, `Usuario`, `Modalidade`)

**Files:**
- Create: `models/__init__.py`
- Create: `models/funcao.py`
- Create: `models/usuario.py`
- Create: `models/modalidade.py`
- Test: `tests/test_models_auth.py`

**Interfaces:**
- Consumes: `database.get_connection()`
- Produces:
  - `Funcao.listar_todas() -> list[dict]` (`[{"id": int, "descricao": str}]`)
  - `Funcao.buscar_por_descricao(descricao: str) -> dict | None`
  - `Modalidade.listar_todas() -> list[dict]` (`[{"id": int, "descricao": str}]`)
  - `Modalidade.buscar_por_id(modalidade_id: int) -> dict | None`
  - `Usuario.autenticar(email: str, senha: str) -> dict | None` (`{"id": int, "nome": str, "email": str, "funcao_id": int, "funcao": str}`)
  - `Usuario.criar(nome: str, email: str, senha: str) -> int` (valida `len(senha) <= 20`, verifica duplicidade de e-mail levantando `ValueError`, vincula à função `'normal'`)
  - `Usuario.listar_todos() -> list[dict]` (`[{"id": int, "nome": str, "email": str, "funcao_id": int, "funcao": str}]`)
  - `Usuario.atualizar_funcao(usuario_id: int, nova_funcao_descricao: str) -> bool`

- [ ] **Step 1: Escrever os testes de `Funcao`, `Modalidade` e `Usuario` em `tests/test_models_auth.py`**

```python
import pytest
from unittest.mock import MagicMock, patch
from models.usuario import Usuario
from models.modalidade import Modalidade

def test_usuario_criar_rejeita_senha_maior_que_20_chars():
    with pytest.raises(ValueError, match="20 caracteres"):
        Usuario.criar("Teste", "teste@ifrs.edu.br", "a" * 21)

def test_usuario_criar_rejeita_email_duplicado():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = (99,)  # email já existe

    with patch("models.usuario.get_connection", return_value=mock_conn):
        with pytest.raises(ValueError, match="E-mail já cadastrado"):
            Usuario.criar("Teste", "dup@ifrs.edu.br", "123456")

def test_usuario_autenticar_retorna_dados_com_funcao():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = (1, "Admin User", "admin@pense.com", 1, "Admin")

    with patch("models.usuario.get_connection", return_value=mock_conn):
        user = Usuario.autenticar("admin@pense.com", "admin123")

    assert user == {
        "id": 1,
        "nome": "Admin User",
        "email": "admin@pense.com",
        "funcao_id": 1,
        "funcao": "Admin",
    }
```

- [ ] **Step 2: Rodar os testes para verificar que falham**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models_auth.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'models'`)

- [ ] **Step 3: Implementar `models/funcao.py`, `models/modalidade.py`, `models/usuario.py` e `models/__init__.py`**

Implementar os métodos com SQL puro parametrizado (`SELECT`, `INSERT ... RETURNING id`, `UPDATE usuarios SET funcao_id = ...`).

- [ ] **Step 4: Rodar os testes para verificar que passam**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models_auth.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add models/ tests/test_models_auth.py
git commit -m "feat(models): add Funcao, Modalidade and Usuario SQL models"
```

---

### Task 3: Models de Submissão (`Autor`, `Instituicao`, `Formulario`)

**Files:**
- Create: `models/autor.py`
- Create: `models/instituicao.py`
- Create: `models/formulario.py`
- Modify: `models/__init__.py`
- Test: `tests/test_models_formulario.py`

**Interfaces:**
- Consumes: `database.get_connection()`
- Produces:
  - `Autor.obter_ou_criar(cur, nome: str, email: str, area: str, cidade: str) -> int`
  - `Instituicao.obter_ou_criar(cur, nome: str, cidade: str) -> int`
  - `Formulario.criar(dados_autor: dict, dados_instituicao: dict, dados_form: dict, arquivo_bytes: bytes) -> int`
  - `Formulario.listar_todos() -> list[dict]`
  - `Formulario.buscar_por_id(form_id: int) -> dict | None`
  - `Formulario.buscar_arquivo(form_id: int) -> tuple[bytes, str] | None`
  - `Formulario.atualizar(form_id: int, dados_autor: dict, dados_instituicao: dict, dados_form: dict, arquivo_bytes: bytes | None = None) -> bool`
  - `Formulario.excluir(form_id: int) -> bool`

- [ ] **Step 1: Escrever os testes de transação, criação, atualização sem e com novo PDF em `tests/test_models_formulario.py`**

```python
from unittest.mock import MagicMock, patch
from models.formulario import Formulario

def test_formulario_criar_executa_transacao_unica():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    # Simula autor novo -> id 10, instituicao nova -> id 20, formulario -> id 30
    mock_cur.fetchone.side_effect = [None, (10,), None, (20,), (30,)]

    with patch("models.formulario.get_connection", return_value=mock_conn):
        novo_id = Formulario.criar(
            dados_autor={"nome": "Ana", "email": "ana@ifrs.edu.br", "area": "IA", "cidade": "Farroupilha"},
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

def test_formulario_atualizar_sem_novo_pdf_mantem_arquivo_existente():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.side_effect = [(10, 20), (10,), (20,)]  # busca atual + ids autor/instituicao
    mock_cur.rowcount = 1

    with patch("models.formulario.get_connection", return_value=mock_conn):
        ok = Formulario.atualizar(
            form_id=5,
            dados_autor={"nome": "Ana", "email": "ana@ifrs.edu.br", "area": "IA", "cidade": "Farroupilha"},
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
    update_queries = [c.args[0] for c in mock_cur.execute.call_args_list if "UPDATE formularios" in c.args[0]]
    assert len(update_queries) == 1
    assert "arquivo =" not in update_queries[0]
```

- [ ] **Step 2: Rodar os testes para verificar que falham**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models_formulario.py -v`
Expected: FAIL (`ModuleNotFoundError: No module named 'models.formulario'`)

- [ ] **Step 3: Implementar `models/autor.py`, `models/instituicao.py` e `models/formulario.py`**

Implementar `Autor.obter_ou_criar`, `Instituicao.obter_ou_criar` e os métodos de `Formulario` com `JOIN` entre `formularios`, `autores`, `instituicoes` e `modalidades_formularios`, validando tamanhos máximos (`titulo` <= 50, `palavra_chave` <= 100, `area_conhecimento` <= 255).

- [ ] **Step 4: Rodar os testes para verificar que passam**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_models_formulario.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```powershell
git add models/ tests/test_models_formulario.py
git commit -m "feat(models): add Autor, Instituicao and Formulario transactional models"
```

---

### Task 4: Controllers e Templates de Autenticação e Gestão de Usuários

**Files:**
- Create: `controllers/__init__.py`
- Create: `controllers/decorators.py`
- Create: `controllers/auth_controller.py`
- Create: `controllers/usuario_controller.py`
- Create: `templates/login.html`
- Create: `templates/cadastro.html`
- Create: `templates/usuarios.html`
- Test: `tests/test_controllers_auth_usuarios.py`

**Interfaces:**
- Consumes: `Usuario`, `Funcao` de `models/`
- Produces:
  - `decorators.login_required(view)` e `decorators.admin_required(view)`
  - `auth_bp` (`Blueprint("auth", __name__)`): rotas `GET/POST /login`, `GET/POST /cadastro`, `POST/GET /logout`
  - `usuario_bp` (`Blueprint("usuario", __name__)`): rotas `GET /usuarios`, `POST /usuarios/<int:id>/promover`

- [ ] **Step 1: Escrever os testes de autenticação, proteção de rota e promoção a Admin em `tests/test_controllers_auth_usuarios.py`**

```python
from unittest.mock import patch
from app import create_app

def test_rota_protegida_redireciona_para_login():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    resp = client.get("/")
    assert resp.status_code == 302
    assert "/login" in resp.headers["Location"]

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

    with patch("controllers.usuario_controller.Usuario.atualizar_funcao", return_value=True) as mock_update:
        resp = client.post("/usuarios/2/promover", follow_redirects=False)

    assert resp.status_code == 302
    mock_update.assert_called_once_with(2, "Admin")
```

- [ ] **Step 2: Rodar os testes para verificar que falham**

Run: `.\.venv\Scripts\python.exe -m pytest tests/test_controllers_auth_usuarios.py -v`
Expected: FAIL (`ImportError: cannot import name 'create_app' from 'app'`)

- [ ] **Step 3: Implementar `controllers/decorators.py`, `controllers/auth_controller.py`, `controllers/usuario_controller.py` e templates `login.html`, `cadastro.html`, `usuarios.html`**

Criar os decorators de sessão, rotas de login/cadastro/logout e painel de usuários para promoção a `Admin`.

- [ ] **Step 4: Implementar Task 5 em seguida ou criar stub de `create_app` em `app.py` para validar Task 4**

Integrar os Blueprints em `app.py` e rodar `pytest tests/test_controllers_auth_usuarios.py -v`.

---

### Task 5: Controller de Formulários, Templates MVC Completos e Entrypoint `app.py`

**Files:**
- Create: `controllers/formulario_controller.py`
- Modify: `app.py`
- Modify: `templates/base.html`
- Modify: `templates/index.html`
- Modify: `templates/formulario.html`
- Modify: `templates/detalhe.html`
- Modify: `static/css/style.css`
- Test: `tests/test_controllers_formulario.py`

**Interfaces:**
- Consumes: `Formulario`, `Modalidade` de `models/`; `login_required`, `admin_required` de `controllers/decorators.py`
- Produces:
  - `formulario_bp` (`Blueprint("formulario", __name__)`) com endpoints compatíveis (`formulario.index`, `formulario.criar`, `formulario.detalhe`, `formulario.arquivo`, `formulario.editar`, `formulario.excluir`)
  - `app.create_app(testing: bool = False) -> Flask` e instância global `app`

- [ ] **Step 1: Escrever os testes de submissão, download de PDF (`BYTEA`) e permissões Admin em `tests/test_controllers_formulario.py`**

```python
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

    with patch("controllers.formulario_controller.Formulario.buscar_arquivo", return_value=(b"%PDF-1.4 test", "Teoria Quantica")):
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

def test_submissao_rejeita_arquivo_nao_pdf():
    with patch("database.init_db"):
        app = create_app(testing=True)
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["usuario_id"] = 2
        sess["usuario_nome"] = "Normal"
        sess["usuario_funcao"] = "normal"

    with patch("controllers.formulario_controller.Modalidade.listar_todas", return_value=[{"id": 1, "descricao": "Pesquisa"}]), \
         patch("controllers.formulario_controller.Modalidade.buscar_por_id", return_value={"id": 1, "descricao": "Pesquisa"}):
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
```

- [ ] **Step 2: Implementar `controllers/formulario_controller.py`, `app.py` e atualizar `templates/` e `static/css/style.css`**

- Em `base.html`: exibir menu dinâmico com `INÍCIO`, `FORMULÁRIO`, `USUÁRIOS` (somente se `session.get('usuario_funcao') == 'Admin'`) e botão `SAIR` (quando logado).
- Em `formulario.html`: organizar os 3 blocos (Dados do Autor, Dados da Instituição, Dados do Trabalho com `palavra_chave`, `area_conhecimento`, `modalidade_id` e upload PDF), suportando tanto criação quanto edição.
- Em `index.html` e `detalhe.html`: usar `t.id` (do banco) em vez de `loop.index0`, exibir botão de visualizar/baixar PDF (`/trabalho/<id>/arquivo`) e botões `Editar` e `Excluir` visíveis apenas para `Admin`.

- [ ] **Step 3: Rodar toda a suíte de testes**

Run: `.\.venv\Scripts\python.exe -m pytest -v`
Expected: Todos os testes passando (`test_database.py`, `test_models_auth.py`, `test_models_formulario.py`, `test_controllers_auth_usuarios.py`, `test_controllers_formulario.py`).

- [ ] **Step 4: Commit final da estrutura MVC**

```powershell
git add app.py controllers/ templates/ static/css/style.css tests/
git commit -m "feat(mvc): complete MVC controllers, templates and BYTEA PDF CRUD"
```
