import psycopg2
from database import get_connection
from models.arquivo import Arquivo
from models.autor import Autor
from models.instituicao import Instituicao


class Formulario:
    @staticmethod
    def _validar_dados_form(dados_form: dict) -> dict:
        titulo = (dados_form.get("titulo") or "").strip()
        resumo = (dados_form.get("resumo") or "").strip()
        palavra_chave = (dados_form.get("palavra_chave") or "").strip()
        area_conhecimento = (dados_form.get("area_conhecimento") or "").strip()
        modalidade_id = dados_form.get("modalidade_id")

        if not (titulo and resumo and palavra_chave and area_conhecimento and modalidade_id):
            raise ValueError("Preencha todos os campos do formulário.")
        if len(titulo) > 50:
            raise ValueError("O título deve ter no máximo 50 caracteres.")
        if len(palavra_chave) > 100:
            raise ValueError("A palavra-chave deve ter no máximo 100 caracteres.")
        if len(area_conhecimento) > 255:
            raise ValueError("A área do conhecimento deve ter no máximo 255 caracteres.")

        return {
            "modalidade_id": int(modalidade_id),
            "titulo": titulo,
            "resumo": resumo,
            "palavra_chave": palavra_chave,
            "area_conhecimento": area_conhecimento,
        }

    @staticmethod
    def criar(
        dados_autor: dict,
        dados_instituicao: dict,
        dados_form: dict,
        arquivo_bytes: bytes,
        nome_arquivo: str = "trabalho.pdf",
        usuario_id: int | None = None,
        content_type_arquivo: str = "application/pdf",
        imagem: tuple[str, str, bytes] | None = None,
    ) -> int:
        autor_limpo = Autor.validar_dados(dados_autor)
        inst_limpa = Instituicao.validar_dados(dados_instituicao)
        form_limpo = Formulario._validar_dados_form(dados_form)

        if not arquivo_bytes:
            raise ValueError("O envio do arquivo do documento é obrigatório.")

        with get_connection() as conn:
            with conn.cursor() as cur:
                autor_id = Autor.obter_ou_criar(
                    cur,
                    autor_limpo["nome"],
                    autor_limpo["email"],
                    autor_limpo["area"],
                    autor_limpo["cidade"],
                )
                instituicao_id = Instituicao.obter_ou_criar(
                    cur,
                    inst_limpa["nome"],
                    inst_limpa["cidade"],
                )
                arquivo_id = Arquivo.criar(
                    cur,
                    nome_arquivo or f"{form_limpo['titulo']}.pdf",
                    content_type_arquivo or "application/pdf",
                    arquivo_bytes,
                )
                imagem_arquivo_id = None
                if imagem is not None:
                    nome_img, tipo_img, bytes_img = imagem
                    imagem_arquivo_id = Arquivo.criar(
                        cur, nome_img, tipo_img, bytes_img
                    )

                cur.execute(
                    """
                    INSERT INTO formularios (
                        usuario_id, autor_id, modalidade_id, instituicao_id, arquivo_id, imagem_arquivo_id,
                        titulo, resumo, arquivo, palavra_chave, area_conhecimento
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING id;
                    """,
                    (
                        usuario_id,
                        autor_id,
                        form_limpo["modalidade_id"],
                        instituicao_id,
                        arquivo_id,
                        imagem_arquivo_id,
                        form_limpo["titulo"],
                        form_limpo["resumo"],
                        psycopg2.Binary(arquivo_bytes),
                        form_limpo["palavra_chave"],
                        form_limpo["area_conhecimento"],
                    ),
                )
                novo_id = cur.fetchone()[0]
            conn.commit()
            return novo_id

    @staticmethod
    def listar_todos() -> list[dict]:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        f.id,
                        f.titulo,
                        f.resumo,
                        f.palavra_chave,
                        f.area_conhecimento,
                        m.id AS modalidade_id,
                        m.descricao AS modalidade,
                        a.id AS autor_id,
                        a.nome AS autor_nome,
                        a.email AS autor_email,
                        a.area AS autor_area,
                        a.cidade AS autor_cidade,
                        i.id AS instituicao_id,
                        i.nome AS instituicao_nome,
                        i.cidade AS instituicao_cidade,
                        f.usuario_id,
                        u.foto_arquivo_id AS usuario_foto_id,
                        f.arquivo_id,
                        f.imagem_arquivo_id
                    FROM formularios f
                    JOIN modalidades_formularios m ON m.id = f.modalidade_id
                    JOIN autores a ON a.id = f.autor_id
                    JOIN instituicoes i ON i.id = f.instituicao_id
                    LEFT JOIN usuarios u ON u.id = f.usuario_id
                    ORDER BY f.id DESC;
                    """
                )
                rows = cur.fetchall()
                return [Formulario._row_to_dict(r) for r in rows]

    @staticmethod
    def buscar_por_id(form_id: int) -> dict | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        f.id,
                        f.titulo,
                        f.resumo,
                        f.palavra_chave,
                        f.area_conhecimento,
                        m.id AS modalidade_id,
                        m.descricao AS modalidade,
                        a.id AS autor_id,
                        a.nome AS autor_nome,
                        a.email AS autor_email,
                        a.area AS autor_area,
                        a.cidade AS autor_cidade,
                        i.id AS instituicao_id,
                        i.nome AS instituicao_nome,
                        i.cidade AS instituicao_cidade,
                        f.usuario_id,
                        u.foto_arquivo_id AS usuario_foto_id,
                        f.arquivo_id,
                        f.imagem_arquivo_id
                    FROM formularios f
                    JOIN modalidades_formularios m ON m.id = f.modalidade_id
                    JOIN autores a ON a.id = f.autor_id
                    JOIN instituicoes i ON i.id = f.instituicao_id
                    LEFT JOIN usuarios u ON u.id = f.usuario_id
                    WHERE f.id = %s
                    LIMIT 1;
                    """,
                    (form_id,),
                )
                row = cur.fetchone()
                if not row:
                    return None
                return Formulario._row_to_dict(row)

    @staticmethod
    def buscar_arquivo(form_id: int) -> tuple | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT COALESCE(arq.dados, f.arquivo), f.titulo, arq.nome, arq.content_type
                    FROM formularios f
                    LEFT JOIN arquivos arq ON arq.id = f.arquivo_id
                    WHERE f.id = %s
                    LIMIT 1;
                    """,
                    (form_id,),
                )
                row = cur.fetchone()
                if not row or row[0] is None:
                    return None
                if len(row) >= 4:
                    return bytes(row[0]), row[1], row[2], row[3]
                return bytes(row[0]), row[1]

    @staticmethod
    def atualizar(
        form_id: int,
        dados_autor: dict,
        dados_instituicao: dict,
        dados_form: dict,
        arquivo_bytes: bytes | None = None,
        nome_arquivo: str = "trabalho.pdf",
        content_type_arquivo: str = "application/pdf",
        imagem: tuple[str, str, bytes] | None = None,
    ) -> bool:
        autor_limpo = Autor.validar_dados(dados_autor)
        inst_limpa = Instituicao.validar_dados(dados_instituicao)
        form_limpo = Formulario._validar_dados_form(dados_form)

        with get_connection() as conn:
            with conn.cursor() as cur:
                autor_id = Autor.obter_ou_criar(
                    cur,
                    autor_limpo["nome"],
                    autor_limpo["email"],
                    autor_limpo["area"],
                    autor_limpo["cidade"],
                )
                instituicao_id = Instituicao.obter_ou_criar(
                    cur,
                    inst_limpa["nome"],
                    inst_limpa["cidade"],
                )

                campos_sql = [
                    "autor_id = %s",
                    "modalidade_id = %s",
                    "instituicao_id = %s",
                    "titulo = %s",
                    "resumo = %s",
                    "palavra_chave = %s",
                    "area_conhecimento = %s",
                ]
                valores = [
                    autor_id,
                    form_limpo["modalidade_id"],
                    instituicao_id,
                    form_limpo["titulo"],
                    form_limpo["resumo"],
                    form_limpo["palavra_chave"],
                    form_limpo["area_conhecimento"],
                ]

                if arquivo_bytes is not None:
                    arquivo_id = Arquivo.criar(
                        cur,
                        nome_arquivo or f"{form_limpo['titulo']}.pdf",
                        content_type_arquivo or "application/pdf",
                        arquivo_bytes,
                    )
                    campos_sql.extend(["arquivo_id = %s", "arquivo = %s"])
                    valores.extend([arquivo_id, psycopg2.Binary(arquivo_bytes)])

                if imagem is not None:
                    nome_img, tipo_img, bytes_img = imagem
                    imagem_id = Arquivo.criar(cur, nome_img, tipo_img, bytes_img)
                    campos_sql.append("imagem_arquivo_id = %s")
                    valores.append(imagem_id)

                valores.append(form_id)
                cur.execute(
                    f"UPDATE formularios SET {', '.join(campos_sql)} WHERE id = %s;",
                    tuple(valores),
                )
                atualizado = cur.rowcount > 0
            conn.commit()
            return atualizado

    @staticmethod
    def excluir(form_id: int) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute("DELETE FROM formularios WHERE id = %s;", (form_id,))
                excluido = cur.rowcount > 0
            conn.commit()
            return excluido

    @staticmethod
    def _row_to_dict(r: tuple) -> dict:
        return {
            "id": r[0],
            "titulo": r[1],
            "resumo": r[2],
            "palavra_chave": r[3],
            "area_conhecimento": r[4],
            "modalidade_id": r[5],
            "modalidade": r[6],
            "autor_id": r[7],
            "autor": r[8],
            "autor_nome": r[8],
            "autor_email": r[9],
            "autor_area": r[10],
            "autor_cidade": r[11],
            "instituicao_id": r[12],
            "campus": r[13],
            "instituicao_nome": r[13],
            "instituicao_cidade": r[14],
            "usuario_id": r[15] if len(r) > 15 else None,
            "usuario_foto_id": r[16] if len(r) > 16 else None,
            "arquivo_id": r[17] if len(r) > 17 else None,
            "imagem_arquivo_id": r[18] if len(r) > 18 else None,
        }
