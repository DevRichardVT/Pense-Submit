import io
from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    send_file,
    session,
    url_for,
)
from werkzeug.utils import secure_filename
from controllers.decorators import admin_required, login_required
from models.arquivo import Arquivo
from models.formulario import Formulario
from models.modalidade import Modalidade

formulario_bp = Blueprint("formulario", __name__)


def _ler_pdf_enviado(arquivo, obrigatorio: bool = True) -> tuple[bytes, str] | None:
    if not arquivo or not arquivo.filename:
        if obrigatorio:
            raise ValueError("O envio do arquivo PDF é obrigatório.")
        return None

    nome_seguro = secure_filename(arquivo.filename)
    if not nome_seguro.lower().endswith(".pdf"):
        raise ValueError("O arquivo precisa ser um PDF (.pdf).")

    conteudo = arquivo.read()
    if not conteudo:
        raise ValueError("O arquivo PDF enviado está vazio.")
    return conteudo, nome_seguro


def _extrair_dados_requisicao(req):
    dados_autor = {
        "nome": req.form.get("autor_nome", "").strip(),
        "email": req.form.get("autor_email", "").strip(),
        "area": req.form.get("autor_area", "").strip(),
        "cidade": req.form.get("autor_cidade", "").strip(),
    }
    dados_instituicao = {
        "nome": req.form.get("instituicao_nome", "").strip(),
        "cidade": req.form.get("instituicao_cidade", "").strip(),
    }
    dados_form = {
        "modalidade_id": req.form.get("modalidade_id", "").strip(),
        "titulo": req.form.get("titulo", "").strip(),
        "palavra_chave": req.form.get("palavra_chave", "").strip(),
        "area_conhecimento": req.form.get("area_conhecimento", "").strip(),
        "resumo": req.form.get("resumo", "").strip(),
    }
    return dados_autor, dados_instituicao, dados_form


def _montar_estado_formulario(
    dados_autor: dict, dados_instituicao: dict, dados_form: dict, base: dict | None = None
) -> dict:
    estado = dict(base or {})
    estado.update(dados_form)
    estado.update(
        {
            "autor_nome": dados_autor.get("nome", ""),
            "autor_email": dados_autor.get("email", ""),
            "autor_area": dados_autor.get("area", ""),
            "autor_cidade": dados_autor.get("cidade", ""),
            "instituicao_nome": dados_instituicao.get("nome", ""),
            "instituicao_cidade": dados_instituicao.get("cidade", ""),
        }
    )
    return estado


@formulario_bp.route("/")
@login_required
def index():
    trabalhos = Formulario.listar_todos()
    return render_template("index.html", trabalhos=trabalhos)


@formulario_bp.route("/formulario", methods=["GET", "POST"])
@login_required
def criar():
    modalidades = Modalidade.listar_todas()

    if request.method == "POST":
        dados_autor, dados_instituicao, dados_form = _extrair_dados_requisicao(request)

        try:
            mod_id = int(dados_form["modalidade_id"]) if dados_form["modalidade_id"] else 0
        except ValueError:
            mod_id = 0

        if not mod_id or not Modalidade.buscar_por_id(mod_id):
            flash("Escolha uma modalidade válida.")
            return (
                render_template(
                    "formulario.html",
                    modalidades=modalidades,
                    edicao=False,
                    form_atual=_montar_estado_formulario(
                        dados_autor, dados_instituicao, dados_form
                    ),
                ),
                400,
            )

        try:
            pdf_info = _ler_pdf_enviado(request.files.get("arquivo"), obrigatorio=True)
            arquivo_bytes, nome_pdf = pdf_info
            Formulario.criar(
                dados_autor=dados_autor,
                dados_instituicao=dados_instituicao,
                dados_form=dados_form,
                arquivo_bytes=arquivo_bytes,
                nome_arquivo=nome_pdf,
                usuario_id=session.get("usuario_id"),
            )
        except ValueError as erro:
            flash(str(erro))
            return (
                render_template(
                    "formulario.html",
                    modalidades=modalidades,
                    edicao=False,
                    form_atual=_montar_estado_formulario(
                        dados_autor, dados_instituicao, dados_form
                    ),
                ),
                400,
            )

        flash("Trabalho enviado com sucesso!")
        return redirect(url_for("formulario.index"))

    return render_template(
        "formulario.html", modalidades=modalidades, edicao=False, form_atual={}
    )


@formulario_bp.route("/trabalho/<int:id>")
@login_required
def detalhe(id: int):
    trabalho = Formulario.buscar_por_id(id)
    if not trabalho:
        abort(404)
    return render_template("detalhe.html", t=trabalho)


@formulario_bp.route("/arquivos/<int:id>")
@login_required
def ver_arquivo(id: int):
    arq = Arquivo.buscar_por_id(id)
    if not arq:
        abort(404)
    return send_file(
        io.BytesIO(arq["dados"]),
        mimetype=arq["content_type"],
        as_attachment=False,
        download_name=arq["nome"],
    )


@formulario_bp.route("/trabalho/<int:id>/arquivo")
@login_required
def arquivo(id: int):
    resultado = Formulario.buscar_arquivo(id)
    if not resultado:
        abort(404)
    arquivo_bytes, titulo = resultado
    nome_download = secure_filename(f"{titulo}.pdf") or f"trabalho_{id}.pdf"
    return send_file(
        io.BytesIO(arquivo_bytes),
        mimetype="application/pdf",
        as_attachment=False,
        download_name=nome_download,
    )


@formulario_bp.route("/trabalho/<int:id>/editar", methods=["GET", "POST"])
@admin_required
def editar(id: int):
    trabalho = Formulario.buscar_por_id(id)
    if not trabalho:
        abort(404)

    modalidades = Modalidade.listar_todas()

    if request.method == "POST":
        dados_autor, dados_instituicao, dados_form = _extrair_dados_requisicao(request)

        try:
            mod_id = int(dados_form["modalidade_id"]) if dados_form["modalidade_id"] else 0
        except ValueError:
            mod_id = 0

        if not mod_id or not Modalidade.buscar_por_id(mod_id):
            flash("Escolha uma modalidade válida.")
            return (
                render_template(
                    "formulario.html",
                    modalidades=modalidades,
                    edicao=True,
                    form_atual=_montar_estado_formulario(
                        dados_autor, dados_instituicao, dados_form, base=trabalho
                    ),
                ),
                400,
            )

        try:
            pdf_info = _ler_pdf_enviado(
                request.files.get("arquivo"), obrigatorio=False
            )
            arquivo_bytes = pdf_info[0] if pdf_info else None
            nome_pdf = pdf_info[1] if pdf_info else "trabalho.pdf"
            Formulario.atualizar(
                form_id=id,
                dados_autor=dados_autor,
                dados_instituicao=dados_instituicao,
                dados_form=dados_form,
                arquivo_bytes=arquivo_bytes,
                nome_arquivo=nome_pdf,
            )
        except ValueError as erro:
            flash(str(erro))
            return (
                render_template(
                    "formulario.html",
                    modalidades=modalidades,
                    edicao=True,
                    form_atual=_montar_estado_formulario(
                        dados_autor, dados_instituicao, dados_form, base=trabalho
                    ),
                ),
                400,
            )

        flash("Trabalho atualizado com sucesso!")
        return redirect(url_for("formulario.detalhe", id=id))

    return render_template(
        "formulario.html", modalidades=modalidades, edicao=True, form_atual=trabalho
    )


@formulario_bp.route("/trabalho/<int:id>/excluir", methods=["POST"])
@admin_required
def excluir(id: int):
    excluido = Formulario.excluir(id)
    if excluido:
        flash("Trabalho excluído com sucesso!")
    else:
        flash("Trabalho não encontrado.")
    return redirect(url_for("formulario.index"))
