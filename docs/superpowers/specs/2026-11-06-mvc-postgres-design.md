# Design Doc: Reestruturação MVC e Integração PostgreSQL (PEnsE-Submite)

**Data:** 2026-11-06  
**Escopo:** Projeto completo de migração de lista em memória para arquitetura MVC com PostgreSQL (SQL puro), autenticação, controle de acesso por funções (`Admin` e `normal`) e CRUD completo de formulários acadêmicos.

---

## 1. Intenção e Motivação (Why)

O **PEnsE-Submite** atualmente funciona como um protótipo em arquivo único (`app.py`) que armazena submissões em uma lista global em memória (`trabalhos`) e salva arquivos PDF localmente em disco. 

O objetivo deste projeto é:
1. Migrar a aplicação para o padrão arquitetural **MVC (Model-View-Controller)**.
2. Substituir a lista em memória por persistência real em **PostgreSQL** utilizando **SQL puro** (`psycopg2`), seguindo o diagrama relacional de 6 tabelas já definido.
3. Implementar controle de acesso com **Login obrigatório** em toda a aplicação, cadastro de novos usuários e diferenciação de permissões entre usuários `normal` (visualização e criação) e `Admin` (CRUD completo de formulários + promoção de outros usuários a `Admin`).
4. Estruturar o cadastro de **Autores** e **Instituições** junto ao envio do formulário para permitir futuras pesquisas e filtros por autor e instituição.

---

## 2. Objetivos, Não-Objetivos e Anti-Objetivos

### Objetivos (Goals)
- Reorganizar o código em camadas **Models**, **Views (`templates/`)** e **Controllers (`controllers/`)** usando Flask Blueprints.
- Conectar ao banco PostgreSQL existente usando SQL puro (`psycopg2-binary`) com queries parametrizadas (`%s`) contra SQL Injection.
- Garantir seed inicial idempotente para as tabelas de domínio (`funcoes`: `Admin`, `normal`; `modalidades_formularios`: `Ensino`, `Pesquisa`, `Extensão`) e para o usuário `Admin` inicial chumbado.
- Proteger todas as rotas da aplicação exigindo login; visitantes não autenticados são redirecionados para `/login`.
- Criar tela de cadastro de novos usuários (todo novo cadastro recebe a função `normal`).
- Criar tela exclusiva para `Admin` listar usuários e promover usuários `normal` para `Admin` (atualizando `funcao_id`).
- Adaptar o formulário de submissão para coletar dados de **Autor** (`nome`, `email`, `area`, `cidade`), **Instituição** (`nome`, `cidade`) e **Formulário** (`titulo`, `palavra_chave`, `area_conhecimento`, `modalidade_id`, `resumo`, `arquivo` PDF).
- Armazenar o arquivo PDF diretamente na coluna `arquivo BYTEA` da tabela `formularios` e disponibilizar rota para visualização/download do PDF a partir dos bytes do banco.
- Permitir ao `Admin` editar e excluir formulários existentes (CRUD completo).

### Não-Objetivos (Non-Goals)
- Implementar tela de busca avançada por autor ou instituição nesta fase (a modelagem já deixará os dados prontos para isso).
- Utilizar ORMs como SQLAlchemy ou ferramentas de migração como Alembic.
- Implementar recuperação de senha por e-mail ou login social.

### Anti-Objetivos (Anti-Goals)
- Não continuar salvando PDFs em pastas locais (`static/uploads` ou `/tmp`), já que o banco exige `arquivo BYTEA NOT NULL`.
- Não permitir que usuários com função `normal` editem/excluam formulários ou acessem rotas administrativas.
- Não descaracterizar a identidade visual atual do PEnsE-Submite (cores, cabeçalho, rodapé e tipografia `Noto Serif`).

---

## 3. Restrições do Schema e Ambiente (Constraints)

A aplicação deve respeitar estritamente o schema PostgreSQL definido:

- **`funcoes`**: `id` (PK, serial), `descricao` (`VARCHAR(255) NOT NULL` — valores: `'Admin'`, `'normal'`).
- **`usuarios`**: `id` (PK, serial), `funcao_id` (`INTEGER NOT NULL` -> `funcoes.id`), `nome` (`VARCHAR(100) NOT NULL`), `email` (`VARCHAR(100) NOT NULL`), `senha` (`VARCHAR(20) NOT NULL`).
  - *Restrição importante:* Como `senha` é `VARCHAR(20)`, o sistema deve validar `maxlength="20"` nos inputs e armazenar a senha respeitando esse limite da coluna no banco.
- **`modalidades_formularios`**: `id` (PK, serial), `descricao` (`VARCHAR(20) NOT NULL` — valores: `'Ensino'`, `'Pesquisa'`, `'Extensão'`).
- **`autores`**: `id` (PK, serial), `nome` (`VARCHAR(100) NOT NULL`), `email` (`VARCHAR(100) NOT NULL`), `area` (`VARCHAR(100) NOT NULL`), `cidade` (`VARCHAR(100) NOT NULL`).
- **`instituicoes`**: `id` (PK, serial), `nome` (`VARCHAR(255) NOT NULL`), `cidade` (`VARCHAR(100) NOT NULL`).
- **`formularios`**:
  - `id` (PK, serial)
  - `autor_id` (`INTEGER NOT NULL` -> `autores.id`)
  - `modalidade_id` (`INTEGER NOT NULL` -> `modalidades_formularios.id`)
  - `instituicao_id` (`INTEGER NOT NULL` -> `instituicoes.id`)
  - `titulo` (`VARCHAR(50) NOT NULL`)
  - `resumo` (`TEXT NOT NULL`)
  - `arquivo` (`BYTEA NOT NULL`)
  - `palavra_chave` (`VARCHAR(100) NOT NULL`)
  - `area_conhecimento` (`VARCHAR(255) NOT NULL`)

Todos os formulários HTML e validações de Controller respeitarão os tamanhos máximos (`VARCHAR(50)` para título, `VARCHAR(100)` para palavra-chave, autor e usuário, `VARCHAR(20)` para senha) para evitar erros do PostgreSQL.

---

## 4. Abordagens Consideradas

1. **MVC Modular com Blueprints e Models com SQL Puro (Escolhida)**
   - **Estrutura:** Pastas `models/` (uma classe por entidade com queries SQL puras), `controllers/` (Flask Blueprints separados por domínio: autenticação, formulários e usuários) e `templates/` (Views Jinja2), além de `database.py` para conexão e seed.
   - **Trade-off:** Equilíbrio ideal entre organização MVC clara, separação de responsabilidades e simplicidade de manutenção sem camadas redundantes.
2. **MVC + Camada de Repository Separada**
   - **Trade-off:** Isola objetos de dados das queries SQL, mas dobra o número de arquivos sem ganho prático para o tamanho do projeto.
3. **MVC Compacto em Arquivos Únicos (`models.py` e `controllers.py`)**
   - **Trade-off:** Rápido inicialmente, mas mistura autenticação, gerenciamento de usuários e CRUD binário de formulários em um único arquivo.

---

## 5. Detalhamento da Arquitetura e Fluxos (How)

### 5.1. Estrutura de Pastas Proposta

```text
Pense-Submit/
├── app.py                        # Entrypoint Flask, registro de Blueprints e configuração de sessão
├── database.py                   # Conexão PostgreSQL (psycopg2), criação de tabelas (se não existirem) e seed inicial
├── requirements.txt              # Flask, psycopg2-binary, python-dotenv
├── .env.example                  # Exemplo de variáveis (DATABASE_URL / DB_HOST, DB_NAME, DB_USER, DB_PASS, SECRET_KEY)
├── models/
│   ├── __init__.py
│   ├── funcao.py                 # Model Funcao (listar, buscar por descrição/id)
│   ├── usuario.py                # Model Usuario (autenticar, criar, listar com função, atualizar função)
│   ├── modalidade.py             # Model Modalidade (listar, buscar por id)
│   ├── autor.py                  # Model Autor (criar, atualizar, buscar)
│   ├── instituicao.py            # Model Instituicao (criar, atualizar, buscar)
│   └── formulario.py             # Model Formulario (CRUD completo com JOINs e leitura do arquivo BYTEA)
├── controllers/
│   ├── __init__.py
│   ├── decorators.py             # @login_required e @admin_required
│   ├── auth_controller.py        # Rotas /login, /cadastro, /logout
│   ├── formulario_controller.py  # Rotas /, /formulario, /trabalho/<id>, /trabalho/<id>/arquivo, /trabalho/<id>/editar, /trabalho/<id>/excluir
│   └── usuario_controller.py     # Rotas /usuarios, /usuarios/<id>/promover (exclusivas Admin)
├── templates/
│   ├── base.html                 # Barra superior adaptada com links dinâmicos (Início, Formulário, Usuários [se Admin], Sair)
│   ├── login.html                # Tela de login
│   ├── cadastro.html             # Tela de cadastro de novo usuário (entra como 'normal')
│   ├── index.html                # Vitrine de trabalhos com ações de Admin (Editar/Excluir)
│   ├── formulario.html           # Criação/Edição unificada (Seção Autor + Seção Instituição + Seção Trabalho)
│   ├── detalhe.html              # Visualização completa de todos os campos + botão Baixar/Ver PDF + ações Admin
│   └── usuarios.html             # Painel Admin para listar usuários e tornar 'normal' em 'Admin'
└── static/
    ├── css/style.css
    └── img/
```

### 5.2. Fluxo de Autenticação e Seed Inicial
- Ao iniciar a aplicação (ou via comando de inicialização em `database.py`), o sistema verifica/cria as tabelas caso ainda não existam, garante os registros de `funcoes` (`Admin`, `normal`), `modalidades_formularios` (`Ensino`, `Pesquisa`, `Extensão`) e garante que o usuário `Admin` padrão chumbado exista na tabela `usuarios`.
- **Login (`/login`):** Verifica `email` e `senha` em `usuarios` (com `JOIN funcoes`). Em caso de sucesso, salva na `session` do Flask: `usuario_id`, `usuario_nome` e `usuario_funcao` (`'Admin'` ou `'normal'`).
- **Cadastro (`/cadastro`):** Recebe `nome`, `email`, `senha`. Verifica se o `email` já está em uso. Insere em `usuarios` com `funcao_id` correspondente a `'normal'`.
- **Proteção de Rotas:** Todas as rotas exceto `/login`, `/cadastro` e arquivos estáticos exigem `@login_required`. Rotas de edição/exclusão de formulário e gestão de usuários exigem `@admin_required`.

### 5.3. Fluxo de Submissão e CRUD de Formulários
- **Criação (`GET/POST /formulario`):**
  - O formulário HTML é dividido visualmente em 3 blocos:
    1. **Dados do Autor:** Nome, E-mail, Área de atuação, Cidade.
    2. **Dados da Instituição:** Nome da Instituição/Campus, Cidade.
    3. **Dados do Trabalho:** Título (máx. 50 caracteres), Palavras-chave (máx. 100 caracteres), Área do Conhecimento (máx. 255 caracteres), Modalidade (radio buttons carregados do banco: Ensino, Pesquisa, Extensão), Resumo e Arquivo PDF (obrigatório na criação).
  - No `POST`, dentro de uma única transação do PostgreSQL:
    1. Insere (ou reutiliza caso já exista exatamente igual) o registro em `autores` e obtém `autor_id`.
    2. Insere (ou reutiliza caso já exista exatamente igual) o registro em `instituicoes` e obtém `instituicao_id`.
    3. Lê os bytes do PDF enviado (`arquivo.read()`) e insere o registro em `formularios` com `psycopg2.Binary(pdf_bytes)`.
- **Listagem (`GET /`) e Detalhes (`GET /trabalho/<int:id>`):**
  - Consulta SQL faz `JOIN` de `formularios` com `autores`, `instituicoes` e `modalidades_formularios`.
  - Na tela de detalhes, exibe todos os novos campos (autor, e-mail e área do autor, instituição e cidade, modalidade, área do conhecimento, palavras-chave, resumo) e um botão **"Visualizar / Baixar PDF"** que aponta para `/trabalho/<int:id>/arquivo`.
- **Download/Visualização do PDF (`GET /trabalho/<int:id>/arquivo`):**
  - Busca apenas a coluna `arquivo` e `titulo` de `formularios` pelo `id` e retorna com `send_file(io.BytesIO(bytes(arquivo)), mimetype="application/pdf", download_name=f"trabalho_{id}.pdf")`.
- **Edição (`GET/POST /trabalho/<int:id>/editar` - Somente Admin):**
  - Reutiliza `formulario.html` preenchido com os dados atuais do formulário, autor e instituição.
  - Na edição, o envio de um novo arquivo PDF é opcional: se o Admin enviar um novo PDF, atualiza a coluna `arquivo`; se deixar em branco, mantém o `BYTEA` já salvo no banco. Atualiza também os dados do formulário, autor e instituição vinculados.
- **Exclusão (`POST /trabalho/<int:id>/excluir` - Somente Admin):**
  - Remove o formulário pelo `id` em `formularios` e redireciona para a tela inicial com mensagem de confirmação.

### 5.4. Fluxo de Gestão de Usuários (Somente Admin)
- **Listagem (`GET /usuarios`):** Lista todos os usuários (`id`, `nome`, `email`, `funcao_descricao`).
- **Promoção (`POST /usuarios/<int:id>/funcao`):** Permite ao `Admin` promover um usuário `normal` para `Admin` (executando `UPDATE usuarios SET funcao_id = %s WHERE id = %s`).

---

## 6. Decisões a Cargo da Implementação (Left to the Builder)

- **Estilização das novas telas (`login.html`, `cadastro.html`, `usuarios.html`) e divisórias do formulário:** Seguir a mesma paleta de cores (`--verde-claro`, `--verde-escuro`, `--cinza-form`, `--branco`) e tipografia já presentes em `static/css/style.css`.
- **Tratamento de Reuso vs Atualização de Autor/Instituição:** Na criação/edição, garantir que a atualização de um trabalho não sobrescreva indevidamente outros trabalhos caso compartilhem registro, ou atualizar diretamente o registro vinculado se for 1:1 por submissão.
- **Configuração de Conexão:** Ler parâmetros do PostgreSQL via variáveis de ambiente (`DATABASE_URL` ou `DB_HOST`, `DB_PORT`, `DB_NAME`, `DB_USER`, `DB_PASSWORD`) com valores padrão locais para facilitar o desenvolvimento.
