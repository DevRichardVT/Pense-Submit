# Design Doc: Melhorias de UX, Wizard, Foto de Usuário e Tabela de Arquivos (PEnsE-Submite)

**Data:** 2026-11-06  
**Escopo:** Melhoria de tamanho pequeno/médio em `PEnsE-Submite` cobrindo prevenção de duplo clique no envio, simplificação do botão Sair, upload opcional de foto de usuário no cadastro com tabela `arquivos` dedicada, exibição da foto do usuário no avatar e no card das submissões, separação do formulário em Wizard de 3 etapas e ajustes de responsividade.

---

## 1. Intenção e Motivação (Why)

Melhorar a experiência de uso do sistema evitando submissões duplicadas por cliques repetidos, deixando a navegação do cabeçalho mais limpa, personalizando os cards e detalhes das submissões com a foto de quem enviou (organizando os arquivos binários em uma tabela própria `arquivos`), guiando o preenchimento do formulário em etapas claras (Wizard) e garantindo que todas as páginas fiquem bem ajustadas em telas móveis e intermediárias.

---

## 2. Objetivos, Não-Objetivos e Anti-Objetivos

### Objetivos (Goals)
- **Botão de envio protegido contra duplo clique:** Desabilitar o botão de submit logo após o primeiro envio válido nos formulários do sistema (`disabled = true` e feedback visual como `"ENVIANDO..."` / `"PROCESSANDO..."`).
- **Botão Sair sem nome do usuário:** Em `templates/base.html`, exibir apenas `SAIR` em vez de `SAIR ({{ session.get('usuario_nome') }})`.
- **Tabela `arquivos` unificada:** Criar a tabela `arquivos (id, nome, content_type, dados BYTEA)` no PostgreSQL para armazenar tanto as fotos de perfil dos usuários quanto os PDFs dos formulários.
- **Foto opcional no cadastro e exibição nas submissões:**
  - Permitir enviar uma imagem opcional (`.jpg`, `.jpeg`, `.png`, `.webp`, `.gif`) em `templates/cadastro.html`.
  - Vincular a foto ao usuário (`usuarios.foto_arquivo_id`) e vincular o formulário ao usuário que o submeteu (`formularios.usuario_id`).
  - Exibir a foto do usuário no avatar e na imagem do card em `templates/index.html`, bem como no avatar de `templates/detalhe.html` (e um avatar na barra superior ou mantendo fallback para `static/img/gato1.jpg` quando o usuário não tiver foto cadastrada).
- **Formulário separado em etapas (Wizard):**
  - Dividir `templates/formulario.html` em 3 etapas: **1. Autores**, **2. Instituição** e **3. Informações do Trabalho**.
  - Impedir o avanço para a próxima etapa caso algum campo obrigatório da etapa atual não esteja preenchido/válido.
- **Responsividade aprimorada:** Ajustar `static/css/style.css` para que cabeçalho, wizard, cards, detalhes e tabela de usuários funcionem sem quebras ou estouro horizontal em celulares e tablets.

### Não-Objetivos (Non-Goals)
- Armazenamento externo em nuvem (S3/GCS) — o projeto usa PostgreSQL `BYTEA`.
- Edição de perfil/troca de foto após o cadastro (fora do escopo pedido).

### Anti-Objetivos (Anti-Goals)
- Não permitir que o usuário avance de etapa no Wizard com campos inválidos ou vazios.
- Não quebrar bancos PostgreSQL já inicializados (usar migração idempotente `ALTER TABLE ... ADD COLUMN IF NOT EXISTS` em `database.py`).

---

## 3. Restrições (Constraints)

- Manter a arquitetura MVC atual (`models/`, `controllers/`, `templates/`) com SQL puro (`psycopg2`).
- Manter compatibilidade retroativa no model/schema caso um formulário antigo ainda tenha `arquivo BYTEA` ou não tenha `usuario_id`/`foto_arquivo_id` preenchido (fallback seguro para `static/img/gato1.jpg`).
- Limite global de upload mantido em 10 MB (`MAX_CONTENT_LENGTH`).

---

## 4. Abordagens Consideradas (Approaches)

1. **Abordagem A — Tabela `arquivos` unificada + Wizard no cliente (JS) com validação completa no servidor (Escolhida)**
   - **Como funciona:** Uma tabela `arquivos` centraliza os binários (`BYTEA`) com `nome` e `content_type`. `usuarios` referencia `foto_arquivo_id` (opcional) e `formularios` referencia `arquivo_id` (PDF) e `usuario_id` (quem enviou). O Wizard divide o `<form>` em 3 `<fieldset class="wizard__etapa">` controlados no cliente com validação nativa (`checkValidity()` / `reportValidity()`) antes de avançar, mantendo um único `POST` ao final.
   - **Trade-off:** Navegação imediata entre etapas sem perder o arquivo selecionado nem precisar gerenciar estado parcial na sessão do Flask.
2. **Abordagem B — Tabelas separadas para fotos/PDFs e Wizard via múltiplas requisições Flask (sessão)**
   - **Trade-off:** Exige múltiplos `POST`s e armazenamento temporário em sessão, complicando a edição de formulários e recarregando a página a cada etapa.

---

## 5. Detalhamento Técnico (How)

### 5.1. Banco de Dados (`schema.sql`, `database.py` e `models/arquivo.py`)
- Nova tabela `arquivos`:
  ```sql
  CREATE TABLE IF NOT EXISTS arquivos (
      id SERIAL PRIMARY KEY,
      nome VARCHAR(255) NOT NULL,
      content_type VARCHAR(100) NOT NULL,
      dados BYTEA NOT NULL
  );
  ```
- Tabela `usuarios`:
  - Ganha coluna `foto_arquivo_id INTEGER REFERENCES arquivos(id) ON DELETE SET NULL`.
- Tabela `formularios`:
  - Ganha coluna `usuario_id INTEGER REFERENCES usuarios(id) ON DELETE SET NULL`.
  - Ganha coluna `arquivo_id INTEGER REFERENCES arquivos(id) ON DELETE SET NULL`.
  - A coluna legada `arquivo BYTEA` passa a aceitar `NULL` em bancos existentes (ou é substituída por `arquivo_id` no `schema.sql`), garantindo que o PDF seja salvo na tabela `arquivos`.
- Novo model `models/arquivo.py` com métodos `criar(cur, nome, content_type, dados_bytes) -> int` e `buscar_por_id(arquivo_id) -> dict | None`.
- Rota `GET /arquivos/<int:id>` (ou `/usuario/<int:id>/foto`) autenticada para servir a imagem do banco com `send_file` e `mimetype=content_type`.

### 5.2. Cadastro com Foto Opcional e Exibição do Avatar
- Em `templates/cadastro.html`: `<form method="POST" enctype="multipart/form-data">` com campo opcional de foto (`accept="image/*"`).
- Em `controllers/auth_controller.py` e `models/usuario.py`:
  - Se uma imagem válida for enviada, grava em `arquivos` e salva `foto_arquivo_id` no usuário; no login, guarda `usuario_foto_id` na sessão (se houver).
- Em `controllers/formulario_controller.py` e `models/formulario.py`:
  - Ao criar um formulário, salva `usuario_id = session.get("usuario_id")` e grava o PDF na tabela `arquivos` (`arquivo_id`).
  - Nas listagens (`listar_todos`) e busca (`buscar_por_id`), faz `LEFT JOIN usuarios u ON u.id = f.usuario_id` trazendo `u.foto_arquivo_id AS usuario_foto_id`.
- Em `templates/index.html`, `templates/detalhe.html` e `templates/base.html`:
  - Se `t.usuario_foto_id` existir, exibe `url_for('formulario.ver_arquivo', id=t.usuario_foto_id)` no `.card__avatar`, `.card__imagem` e `.detalhe__avatar`; caso contrário, usa `static/img/gato1.jpg`.
  - Na barra superior (`base.html`), o botão de sair exibe apenas `SAIR` (e opcionalmente mostra a miniatura do avatar do usuário logado ao lado do menu).

### 5.3. Wizard de 3 Etapas e Proteção contra Duplo Clique
- Em `templates/formulario.html`:
  - Indicador visual das 3 etapas no topo: **1. Autor**, **2. Instituição**, **3. Informações**.
  - Cada etapa fica dentro de um bloco `.wizard-etapa` (`data-step="1"`, `"2"`, `"3"`).
  - O botão **"Próximo"** valida todos os campos (`input`, `textarea`, `select`) da etapa atual com `checkValidity()` / `reportValidity()`; se houver campo vazio ou inválido, bloqueia o avanço e foca no campo.
  - Na etapa 3 fica o botão de envio (`ENVIAR` / `SALVAR ALTERAÇÕES`).
- Prevenção de duplo envio:
  - Ao submeter qualquer `<form>` válido, um listener JS desabilita o botão de submit (`botao.disabled = true`) para impedir múltiplos envios.

### 5.4. Responsividade (`static/css/style.css`)
- Ajustar `.topo` e `.topo__menu` para empilhar/quebrar linha suavemente em telas menores (`<= 768px` e `<= 480px`), sem botões espremidos.
- Ajustar `.grade` com `grid-template-columns: repeat(auto-fit, minmax(280px, 1fr))` ou breakpoints claros (`900px` e `640px`).
- Ajustar paddings do `.formulario`, indicadores do Wizard e botões de ação (`.wizard__acoes`, `.detalhe__acoes`, `.card__acoes`) para ocuparem largura adequada no mobile.
