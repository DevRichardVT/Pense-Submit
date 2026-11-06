# Melhorias de UX, Wizard, Foto de Usuário e Tabela de Arquivos Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Adicionar tabela unificada `arquivos` para fotos de usuário e PDFs, foto opcional no cadastro com exibição no avatar/cards, formulário em Wizard de 3 etapas com bloqueio de avanço e proteção contra duplo clique, botão Sair simplificado e melhorias de responsividade.

**Architecture:** Mantém a estrutura MVC em Flask + PostgreSQL (`psycopg2`). Um novo model `Arquivo` gerencia binários (`BYTEA`, `nome`, `content_type`) na tabela `arquivos`; `usuarios` referencia `foto_arquivo_id` e `formularios` referencia `usuario_id` e `arquivo_id` (com migração idempotente `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` em `database.py`). No frontend, o formulário é dividido em 3 etapas com validação JS (`checkValidity`/`reportValidity`) antes de avançar e bloqueio de botão no `submit`.

**Tech Stack:** Python 3.12, Flask, psycopg2, HTML5/CSS3/JS nativo, pytest.

**Spec:** `docs/superpowers/specs/2026-11-06-melhorias-ux-wizard-arquivos-design.md`

## Global Constraints

- Manter arquitetura MVC (`models/`, `controllers/`, `templates/`) com SQL puro (`psycopg2`).
- Manter compatibilidade retroativa com bancos existentes usando `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` e `ALTER COLUMN arquivo DROP NOT NULL` em `database.py`.
- Foto no cadastro é opcional; quando ausente, usar `static/img/gato1.jpg` como fallback no avatar e no card.
- O botão de sair em `templates/base.html` deve exibir apenas `SAIR` (sem o nome do usuário).

## Review Focus

- Upload de foto com extensão inválida no cadastro (ex.: `.exe` ou `.pdf` no campo de foto) deve exibir erro amigável (`400`) e não quebrar.
- Cadastro sem envio de foto deve funcionar normalmente com `foto_arquivo_id = None`.
- Formulários antigos sem `usuario_id` ou `arquivo_id` (apenas `arquivo BYTEA` legado) devem continuar exibindo fallback de imagem e permitindo download do PDF.
- Duplo clique no botão de envio ou tentativa de avançar etapa do Wizard com campo obrigatório vazio (incluindo radio de modalidade na etapa 3) deve ser bloqueado.
- Em telas pequenas (`<= 640px`), o cabeçalho, os passos do Wizard e os botões de ação não podem estourar horizontalmente.

---

### Task 1: Schema `arquivos`, Migração Idempotente e Model `Arquivo`

**Files:**
- Modify: `schema.sql`
- Modify: `database.py`
- Create: `models/arquivo.py`
- Modify: `models/__init__.py`
- Modify: `tests/test_database.py`

**Interfaces:**
- Produces:
  - `Arquivo.criar(cur, nome: str, content_type: str, dados: bytes) -> int`
  - `Arquivo.buscar_por_id(arquivo_id: int) -> dict | None` returning `{"id": int, "nome": str, "content_type": str, "dados": bytes}`

- [ ] **Step 1: Atualizar `tests/test_database.py` para verificar `CREATE TABLE IF NOT EXISTS arquivos` e migrações**

```python
def test_init_db_executes_schema_and_seed():
    mock_conn = MagicMock()
    mock_cur = MagicMock()
    mock_conn.__enter__.return_value = mock_conn
    mock_conn.cursor.return_value.__enter__.return_value = mock_cur
    mock_cur.fetchone.return_value = None

    with patch("database.get_connection", return_value=mock_conn):
        database.init_db()

    executed_sql = " ".join(call.args[0] for call in mock_cur.execute.call_args_list)
    assert "CREATE TABLE IF NOT EXISTS arquivos" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS usuarios" in executed_sql
    assert "CREATE TABLE IF NOT EXISTS formularios" in executed_sql
    assert "foto_arquivo_id" in executed_sql
    assert "arquivo_id" in executed_sql
    assert mock_conn.commit.called
```

- [ ] **Step 2: Rodar pytest em `tests/test_database.py` e confirmar falha**

Run: `.\.venv\Scripts\pytest tests/test_database.py -v`
Expected: FAIL (`CREATE TABLE IF NOT EXISTS arquivos` ausente)

- [ ] **Step 3: Atualizar `schema.sql`, `database.py` e criar `models/arquivo.py`**

Em `schema.sql` e `database.py`:
- Adicionar tabela `arquivos (id SERIAL PRIMARY KEY, nome VARCHAR(255) NOT NULL, content_type VARCHAR(100) NOT NULL, dados BYTEA NOT NULL)` antes de `usuarios`.
- Em `usuarios`, incluir `foto_arquivo_id INTEGER REFERENCES arquivos(id) ON DELETE SET NULL`.
- Em `formularios`, incluir `usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL`, `arquivo_id INTEGER REFERENCES arquivos(id) ON DELETE SET NULL`, e deixar `arquivo BYTEA` opcional (`NULL`) para compatibilidade.
- No `database.py`, incluir blocos `ALTER TABLE usuarios ADD COLUMN IF NOT EXISTS foto_arquivo_id INTEGER REFERENCES arquivos(id) ON DELETE SET NULL;` e equivalentes para `formularios` (`usuario_id`, `arquivo_id`, e `ALTER COLUMN arquivo DROP NOT NULL`).
- Criar `models/arquivo.py` com `Arquivo.criar(cur, nome, content_type, dados)` e `Arquivo.buscar_por_id(arquivo_id)`.

- [ ] **Step 4: Rodar pytest em `tests/test_database.py` e verificar aprovação**

Run: `.\.venv\Scripts\pytest tests/test_database.py -v`
Expected: PASS

---

### Task 2: Foto Opcional no Cadastro de Usuário e Rota de Arquivos

**Files:**
- Modify: `models/usuario.py`
- Modify: `controllers/auth_controller.py`
- Modify: `controllers/formulario_controller.py`
- Modify: `tests/test_models_auth.py`
- Modify: `tests/test_controllers_auth_usuarios.py`

**Interfaces:**
- Consumes: `Arquivo.criar`, `Arquivo.buscar_por_id`
- Produces:
  - `Usuario.criar(nome: str, email: str, senha: str, foto: tuple[str, str, bytes] | None = None) -> int`
  - `Usuario.autenticar(email: str, senha: str) -> dict | None` (inclui `"foto_arquivo_id": int | None`)
  - Rota `GET /arquivos/<int:id>` em `formulario_bp` (`formulario.ver_arquivo`) que retorna `send_file` com `content_type`.

- [ ] **Step 1: Adicionar testes para `Usuario.criar` com foto, `Usuario.autenticar` com `foto_arquivo_id`, upload inválido no cadastro e rota `/arquivos/<id>`**

Em `tests/test_models_auth.py` e `tests/test_controllers_auth_usuarios.py`:
- Atualizar `test_usuario_autenticar_retorna_dados_com_funcao` para esperar `"foto_arquivo_id": None` (ou ID da foto).
- Adicionar `test_cadastro_aceita_foto_opcional()` e `test_cadastro_rejeita_arquivo_nao_imagem()`.
- Adicionar `test_rota_ver_arquivo_retorna_imagem()`.

- [ ] **Step 2: Rodar pytest e verificar falha**

Run: `.\.venv\Scripts\pytest tests/test_models_auth.py tests/test_controllers_auth_usuarios.py -v`
Expected: FAIL

- [ ] **Step 3: Implementar suporte a foto em `models/usuario.py`, `controllers/auth_controller.py` e rota `/arquivos/<int:id>` em `controllers/formulario_controller.py`**

- Em `models/usuario.py`:
  - `autenticar` e `listar_todos` selecionam `u.foto_arquivo_id`.
  - `criar(nome, email, senha, foto=None)` recebe `foto=(nome_arquivo, content_type, bytes)` opcional; se enviado, chama `Arquivo.criar(cur, ...)` e grava `foto_arquivo_id` em `usuarios`.
- Em `controllers/auth_controller.py`:
  - No `login`, salva `session["usuario_foto_id"] = usuario.get("foto_arquivo_id")`.
  - No `cadastro`, lê `request.files.get("foto")`; se houver arquivo, valida extensão/mimetype de imagem (`.png`, `.jpg`, `.jpeg`, `.webp`, `.gif`), lê os bytes e passa para `Usuario.criar`.
- Em `controllers/formulario_controller.py`:
  - Adicionar `@formulario_bp.route("/arquivos/<int:id>")` (`ver_arquivo`) protegido por `@login_required` que busca `Arquivo.buscar_por_id(id)` e retorna `send_file(io.BytesIO(arq["dados"]), mimetype=arq["content_type"], download_name=arq["nome"])`.

- [ ] **Step 4: Rodar pytest e verificar aprovação**

Run: `.\.venv\Scripts\pytest tests/test_models_auth.py tests/test_controllers_auth_usuarios.py -v`
Expected: PASS

---

### Task 3: Vincular Submissão ao Usuário e à Tabela `arquivos`

**Files:**
- Modify: `models/formulario.py`
- Modify: `controllers/formulario_controller.py`
- Modify: `tests/test_models_formulario.py`
- Modify: `tests/test_controllers_formulario.py`

**Interfaces:**
- Consumes: `Arquivo.criar`, `Arquivo.buscar_por_id`
- Produces:
  - `Formulario.criar(dados_autor, dados_instituicao, dados_form, arquivo_bytes, nome_arquivo="trabalho.pdf", usuario_id=None) -> int`
  - `Formulario.listar_todos()` e `Formulario.buscar_por_id(id)` incluem `"usuario_id"`, `"usuario_foto_id"` e `"arquivo_id"`.
  - `Formulario.buscar_arquivo(id)` lê de `arquivos` via `arquivo_id` (com fallback para `formularios.arquivo` legado).

- [ ] **Step 1: Atualizar testes em `tests/test_models_formulario.py` e `tests/test_controllers_formulario.py`**

- Verificar que `Formulario.criar` insere o PDF na tabela `arquivos` e salva `arquivo_id` e `usuario_id` em `formularios`.
- Verificar que `Formulario.listar_todos` e `buscar_por_id` retornam `usuario_foto_id`.

- [ ] **Step 2: Rodar pytest e verificar falha**

Run: `.\.venv\Scripts\pytest tests/test_models_formulario.py tests/test_controllers_formulario.py -v`
Expected: FAIL

- [ ] **Step 3: Atualizar `models/formulario.py` e `controllers/formulario_controller.py`**

- Em `models/formulario.py`:
  - Em `criar`: chamar `Arquivo.criar(cur, nome_arquivo, "application/pdf", arquivo_bytes)` e inserir `usuario_id`, `arquivo_id` e `arquivo` em `formularios`.
  - Em `atualizar`: quando `arquivo_bytes` for enviado, criar novo registro em `arquivos` e atualizar `arquivo_id`.
  - Em `listar_todos` e `buscar_por_id`: fazer `LEFT JOIN usuarios u ON u.id = f.usuario_id` e retornar `u.id AS usuario_id, u.foto_arquivo_id AS usuario_foto_id, f.arquivo_id`.
  - Em `buscar_arquivo`: fazer `LEFT JOIN arquivos arq ON arq.id = f.arquivo_id` e retornar `COALESCE(arq.dados, f.arquivo), f.titulo`.
- Em `controllers/formulario_controller.py`:
  - Passar `usuario_id=session.get("usuario_id")` e o nome seguro do PDF ao criar/atualizar.

- [ ] **Step 4: Rodar pytest e verificar aprovação**

Run: `.\.venv\Scripts\pytest tests/test_models_formulario.py tests/test_controllers_formulario.py -v`
Expected: PASS

---

### Task 4: Templates (Botão Sair, Avatar, Cadastro com Foto, Wizard de 3 Etapas, Anti-Duplo Clique) e Responsividade CSS

**Files:**
- Modify: `templates/base.html`
- Modify: `templates/cadastro.html`
- Modify: `templates/index.html`
- Modify: `templates/detalhe.html`
- Modify: `templates/formulario.html`
- Modify: `static/css/style.css`
- Modify: `tests/test_controllers_formulario.py`

- [ ] **Step 1: Adicionar testes de renderização HTML para o botão `SAIR`, o Wizard e o avatar nos cards**

Em `tests/test_controllers_formulario.py`:
- Verificar que a barra superior renderiza `>SAIR<` (sem o nome do usuário dentro do botão) e mostra o avatar do usuário logado.
- Verificar que `GET /formulario` renderiza as 3 etapas do Wizard (`data-step="1"`, `data-step="2"`, `data-step="3"`) e os botões de navegação.
- Verificar que `GET /` usa `/arquivos/<usuario_foto_id>` quando o trabalho possui `usuario_foto_id`, e `gato1.jpg` quando não possui.

- [ ] **Step 2: Rodar pytest e confirmar falha**

Run: `.\.venv\Scripts\pytest tests/test_controllers_formulario.py -v`
Expected: FAIL

- [ ] **Step 3: Atualizar os templates e `static/css/style.css`**

1. **`templates/base.html`:**
   - Alterar o link de logout para `<a href="{{ url_for('auth.logout') }}">SAIR</a>`.
   - Exibir o avatar do usuário logado no cabeçalho (`url_for('formulario.ver_arquivo', id=session.get('usuario_foto_id'))` se tiver `usuario_foto_id`, senão `url_for('static', filename='img/gato1.jpg')`).
   - Adicionar script global no final de `base.html` que escuta `submit` em qualquer `<form>` e, se `form.checkValidity()` for verdadeiro, desabilita o botão de submit (`botao.disabled = true`) e altera o texto para evitar cliques repetidos.
2. **`templates/cadastro.html`:**
   - Adicionar `enctype="multipart/form-data"` ao `<form>`.
   - Adicionar campo de upload opcional `name="foto"` (`accept=".jpg,.jpeg,.png,.webp,.gif"`) com pré-visualização/nome do arquivo selecionado.
3. **`templates/index.html` e `templates/detalhe.html`:**
   - Se `t.usuario_foto_id` existir, usar `{{ url_for('formulario.ver_arquivo', id=t.usuario_foto_id) }}` em `.card__avatar`, `.card__imagem` e `.detalhe__avatar`; caso contrário, usar `{{ url_for('static', filename='img/gato1.jpg') }}`.
4. **`templates/formulario.html`:**
   - Implementar cabeçalho do Wizard com 3 indicadores de passo (`1. Autor`, `2. Instituição`, `3. Informações`).
   - Envolver cada grupo de campos em `<div class="wizard-etapa" data-step="1|2|3">`.
   - Adicionar botões **Voltar**, **Próximo** e **Enviar / Salvar Alterações**.
   - No JS do Wizard: ao clicar em **Próximo**, validar todos os inputs/textareas da etapa atual usando `checkValidity()` e `reportValidity()`. Só avança para a próxima etapa se todos os campos da etapa atual forem válidos. No `submit`, validar todas as etapas e desabilitar o botão de envio na hora (`disabled = true`, texto `"ENVIANDO..."`).
5. **`static/css/style.css`:**
   - Adicionar estilos para `.wizard-passos`, `.wizard-passo`, `.wizard-etapa`, `.wizard-acoes`, `.topo__avatar` e `button:disabled`.
   - Refinar a responsividade (`@media (max-width: 900px)`, `@media (max-width: 640px)`, `@media (max-width: 480px)`) para cabeçalho, menu, cards, wizard, formulários e tabela de usuários.

- [ ] **Step 4: Rodar toda a suíte de testes**

Run: `.\.venv\Scripts\pytest -v`
Expected: Todos os testes passando.
