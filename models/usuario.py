from werkzeug.security import check_password_hash, generate_password_hash
from database import get_connection
from models.arquivo import Arquivo


class Usuario:
    @staticmethod
    def _verificar_senha(senha_banco: str | None, senha_informada: str) -> bool:
        if senha_banco is None:
            return False
        s = str(senha_banco)
        if s.startswith(("pbkdf2:", "scrypt:")):
            return check_password_hash(s, senha_informada)
        return s == senha_informada

    @staticmethod
    def autenticar(email: str, senha: str) -> dict | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.nome, u.email, u.funcao_id, f.descricao, u.foto_arquivo_id, COALESCE(u.ativo, TRUE), u.senha
                    FROM usuarios u
                    JOIN funcoes f ON f.id = u.funcao_id
                    WHERE LOWER(u.email) = LOWER(%s)
                      AND COALESCE(u.ativo, TRUE) = TRUE
                    LIMIT 1;
                    """,
                    (email.strip(),),
                )
                row = cur.fetchone()
                if not row:
                    return None
                if len(row) > 6 and not row[6]:
                    return None
                if len(row) > 7 and not Usuario._verificar_senha(row[7], senha):
                    return None
                return {
                    "id": row[0],
                    "nome": row[1],
                    "email": row[2],
                    "funcao_id": row[3],
                    "funcao": row[4],
                    "foto_arquivo_id": row[5] if len(row) > 5 else None,
                }

    @staticmethod
    def criar(
        nome: str,
        email: str,
        senha: str,
        foto: tuple[str, str, bytes] | None = None,
    ) -> int:
        nome = (nome or "").strip()
        email = (email or "").strip()
        if not nome or not email or not senha:
            raise ValueError("Preencha nome, e-mail e senha.")
        if len(nome) > 100 or len(email) > 100:
            raise ValueError("Nome e e-mail devem ter no máximo 100 caracteres.")
        if len(senha) > 20:
            raise ValueError("A senha deve ter no máximo 20 caracteres.")

        senha_hash = generate_password_hash(senha, method="pbkdf2:sha256")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT nome, email
                    FROM usuarios
                    WHERE LOWER(email) = LOWER(%s) OR LOWER(nome) = LOWER(%s)
                    LIMIT 1;
                    """,
                    (email, nome),
                )
                dup = cur.fetchone()
                if dup:
                    if (
                        len(dup) >= 2
                        and str(dup[0]).strip().lower() == nome.lower()
                        and str(dup[1]).strip().lower() != email.lower()
                    ):
                        raise ValueError("Nome de usuário já cadastrado.")
                    raise ValueError("E-mail já cadastrado.")

                cur.execute(
                    "SELECT id FROM funcoes WHERE LOWER(descricao) = 'normal' LIMIT 1;"
                )
                funcao_row = cur.fetchone()
                if not funcao_row:
                    cur.execute(
                        "INSERT INTO funcoes (descricao) VALUES ('normal') RETURNING id;"
                    )
                    funcao_id = cur.fetchone()[0]
                else:
                    funcao_id = funcao_row[0]

                foto_arquivo_id = None
                if foto is not None:
                    nome_foto, content_type, dados_foto = foto
                    foto_arquivo_id = Arquivo.criar(
                        cur, nome_foto, content_type, dados_foto
                    )

                cur.execute(
                    """
                    INSERT INTO usuarios (funcao_id, nome, email, senha, foto_arquivo_id, ativo)
                    VALUES (%s, %s, %s, %s, %s, TRUE)
                    RETURNING id;
                    """,
                    (funcao_id, nome, email, senha_hash, foto_arquivo_id),
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
                    SELECT u.id, u.nome, u.email, u.funcao_id, f.descricao, u.foto_arquivo_id, COALESCE(u.ativo, TRUE)
                    FROM usuarios u
                    JOIN funcoes f ON f.id = u.funcao_id
                    ORDER BY u.id ASC;
                    """
                )
                return [
                    {
                        "id": r[0],
                        "nome": r[1],
                        "email": r[2],
                        "funcao_id": r[3],
                        "funcao": r[4],
                        "foto_arquivo_id": r[5] if len(r) > 5 else None,
                        "ativo": bool(r[6]) if len(r) > 6 else True,
                    }
                    for r in cur.fetchall()
                ]

    @staticmethod
    def buscar_por_id(usuario_id: int) -> dict | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT u.id, u.nome, u.email, u.funcao_id, f.descricao, u.foto_arquivo_id, COALESCE(u.ativo, TRUE)
                    FROM usuarios u
                    JOIN funcoes f ON f.id = u.funcao_id
                    WHERE u.id = %s
                    LIMIT 1;
                    """,
                    (usuario_id,),
                )
                r = cur.fetchone()
                if not r:
                    return None
                return {
                    "id": r[0],
                    "nome": r[1],
                    "email": r[2],
                    "funcao_id": r[3],
                    "funcao": r[4],
                    "foto_arquivo_id": r[5] if len(r) > 5 else None,
                    "ativo": bool(r[6]) if len(r) > 6 else True,
                }

    @staticmethod
    def atualizar_perfil(
        usuario_id: int,
        nome: str,
        foto: tuple[str, str, bytes] | None = None,
        nova_senha: str | None = None,
    ) -> dict:
        nome = (nome or "").strip()
        if not nome:
            raise ValueError("O nome do usuário é obrigatório.")
        if len(nome) > 100:
            raise ValueError("O nome deve ter no máximo 100 caracteres.")
        if nova_senha and len(nova_senha) > 20:
            raise ValueError("A senha deve ter no máximo 20 caracteres.")

        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id FROM usuarios
                    WHERE LOWER(nome) = LOWER(%s) AND id <> %s
                    LIMIT 1;
                    """,
                    (nome, usuario_id),
                )
                if cur.fetchone():
                    raise ValueError("Nome de usuário já cadastrado.")

                campos = ["nome = %s"]
                valores: list = [nome]

                if foto is not None:
                    nome_foto, content_type, dados_foto = foto
                    foto_arquivo_id = Arquivo.criar(
                        cur, nome_foto, content_type, dados_foto
                    )
                    campos.append("foto_arquivo_id = %s")
                    valores.append(foto_arquivo_id)

                if nova_senha:
                    campos.append("senha = %s")
                    valores.append(
                        generate_password_hash(nova_senha, method="pbkdf2:sha256")
                    )

                valores.append(usuario_id)
                cur.execute(
                    f"""
                    UPDATE usuarios
                    SET {', '.join(campos)}
                    WHERE id = %s
                    RETURNING id, nome, foto_arquivo_id;
                    """,
                    tuple(valores),
                )
                row = cur.fetchone()
                if not row:
                    raise ValueError("Usuário não encontrado.")
            conn.commit()
            return {
                "id": row[0],
                "nome": row[1],
                "foto_arquivo_id": row[2],
            }

    @staticmethod
    def atualizar_funcao(usuario_id: int, nova_funcao_descricao: str) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id FROM funcoes WHERE LOWER(descricao) = LOWER(%s) LIMIT 1;",
                    (nova_funcao_descricao,),
                )
                funcao_row = cur.fetchone()
                if not funcao_row:
                    raise ValueError("Função inválida.")

                cur.execute(
                    "UPDATE usuarios SET funcao_id = %s WHERE id = %s;",
                    (funcao_row[0], usuario_id),
                )
                atualizado = cur.rowcount > 0
            conn.commit()
            return atualizado

    @staticmethod
    def definir_ativo(usuario_id: int, ativo: bool) -> bool:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE usuarios SET ativo = %s WHERE id = %s;",
                    (bool(ativo), usuario_id),
                )
                atualizado = cur.rowcount > 0
            conn.commit()
            return atualizado
