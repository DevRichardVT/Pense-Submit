import psycopg2
from database import get_connection


class Arquivo:
    @staticmethod
    def criar(cur, nome: str, content_type: str, dados: bytes) -> int:
        nome_limpo = (nome or "arquivo").strip()[:255] or "arquivo"
        tipo_limpo = (content_type or "application/octet-stream").strip()[:100]
        if not dados:
            raise ValueError("O arquivo enviado está vazio.")

        cur.execute(
            """
            INSERT INTO arquivos (nome, content_type, dados)
            VALUES (%s, %s, %s)
            RETURNING id;
            """,
            (nome_limpo, tipo_limpo, psycopg2.Binary(dados)),
        )
        return cur.fetchone()[0]

    @staticmethod
    def buscar_por_id(arquivo_id: int) -> dict | None:
        with get_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT id, nome, content_type, dados
                    FROM arquivos
                    WHERE id = %s
                    LIMIT 1;
                    """,
                    (arquivo_id,),
                )
                row = cur.fetchone()
                if not row or row[3] is None:
                    return None
                return {
                    "id": row[0],
                    "nome": row[1],
                    "content_type": row[2],
                    "dados": bytes(row[3]),
                }
