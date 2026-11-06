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
from controllers.auth_controller import MAX_TAMANHO_ARQUIVO, _ler_foto_opcional
from controllers.decorators import admin_required, login_required
from models.arquivo import Arquivo
from models.formulario import Formulario
from models.modalidade import Modalidade

formulario_bp = Blueprint("formulario", __name__)

EXTENSOES_DOCUMENTO = {
    ".pdf": "application/pdf",
    ".doc": "application/msword",
    ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    ".odt": "application/vnd.oasis.opendocument.text",
    ".rtf": "application/rtf",
    ".ppt": "application/vnd.ms-powerpoint",
    ".pptx": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    ".xls": "application/vnd.ms-excel",
    ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


def _ler_documento_enviado(
    arquivo, obrigatorio: bool = True
) -> tuple[bytes, str, str] | None:
    if not arquivo or not arquivo.filename:
        if obrigatorio:
            raise ValueError("O envio do arquivo do documento é obrigatório.")
        return None

    nome_seguro = secure_filename(arquivo.filename)
    ext = ""
    if "." in nome_seguro:
        ext = "." + nome_seguro.rsplit(".", 1)[1].lower()

    if ext not in EXTENSOES_DOCUMENTO:
        raise ValueError(
            "Formato inválido. Envie um documento válido (.pdf, .doc, .docx, .odt, .rtf, .ppt, .pptx, .xls, .xlsx)."
        )

    conteudo = arquivo.read()
    if not conteudo:
        raise ValueError("O documento enviado está vazio.")
    if len(conteudo) > MAX_TAMANHO_ARQUIVO:
        raise ValueError("O documento deve ter no máximo 10 MB.")

    return conteudo, nome_seguro, EXTENSOES_DOCUMENTO[ext]


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


@formulario_bp.route("/catalogo")
@login_required
def catalogo():
    trabalhos = Formulario.listar_todos()
    return render_template("catalogo.html", trabalhos=trabalhos)


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
            doc_info = _ler_documento_enviado(
                request.files.get("arquivo"), obrigatorio=True
            )
            arquivo_bytes, nome_doc, content_type_doc = doc_info
            imagem = _ler_foto_opcional(request.files.get("imagem"))
            Formulario.criar(
                dados_autor=dados_autor,
                dados_instituicao=dados_instituicao,
                dados_form=dados_form,
                arquivo_bytes=arquivo_bytes,
                nome_arquivo=nome_doc,
                usuario_id=session.get("usuario_id"),
                content_type_arquivo=content_type_doc,
                imagem=imagem,
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
    arquivo_bytes = resultado[0]
    titulo = resultado[1]
    nome_arq = resultado[2] if len(resultado) > 2 else None
    content_type = (resultado[3] if len(resultado) > 3 else None) or "application/pdf"
    nome_download = (
        secure_filename(nome_arq) if nome_arq else None
    ) or secure_filename(f"{titulo}.pdf") or f"trabalho_{id}.pdf"
    return send_file(
        io.BytesIO(arquivo_bytes),
        mimetype=content_type,
        as_attachment=False,
        download_name=nome_download,
    )


@formulario_bp.route("/trabalho/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id: int):
    trabalho = Formulario.buscar_por_id(id)
    if not trabalho:
        abort(404)

    eh_admin = str(session.get("usuario_funcao", "")).lower() == "admin"
    eh_dono = (
        trabalho.get("usuario_id") is not None
        and int(trabalho["usuario_id"]) == int(session.get("usuario_id", 0))
    )
    if not (eh_admin or eh_dono):
        abort(403)

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
            doc_info = _ler_documento_enviado(
                request.files.get("arquivo"), obrigatorio=False
            )
            arquivo_bytes = doc_info[0] if doc_info else None
            nome_doc = doc_info[1] if doc_info else "trabalho.pdf"
            content_type_doc = doc_info[2] if doc_info else "application/pdf"
            imagem = _ler_foto_opcional(request.files.get("imagem"))
            Formulario.atualizar(
                form_id=id,
                dados_autor=dados_autor,
                dados_instituicao=dados_instituicao,
                dados_form=dados_form,
                arquivo_bytes=arquivo_bytes,
                nome_arquivo=nome_doc,
                content_type_arquivo=content_type_doc,
                imagem=imagem,
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
