from flask import (
    Blueprint,
    abort,
    flash,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from controllers.auth_controller import _ler_foto_opcional
from controllers.decorators import admin_required, login_required
from models.usuario import Usuario

usuario_bp = Blueprint("usuario", __name__)


@usuario_bp.route("/usuarios", methods=["GET"])
@admin_required
def listar():
    usuarios = Usuario.listar_todos()
    return render_template("usuarios.html", usuarios=usuarios)


@usuario_bp.route("/perfil", methods=["GET", "POST"])
@login_required
def meu_perfil():
    return editar(int(session["usuario_id"]))


@usuario_bp.route("/usuarios/<int:id>/editar", methods=["GET", "POST"])
@login_required
def editar(id: int):
    eh_admin = str(session.get("usuario_funcao", "")).lower() == "admin"
    eh_proprio = int(session.get("usuario_id", 0)) == id
    if not (eh_admin or eh_proprio):
        abort(403)

    usuario = Usuario.buscar_por_id(id)
    if not usuario:
        abort(404)

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        nova_senha = request.form.get("nova_senha", "")
        try:
            foto = _ler_foto_opcional(request.files.get("foto"))
            kwargs_update = {"usuario_id": id, "nome": nome, "foto": foto}
            if nova_senha:
                kwargs_update["nova_senha"] = nova_senha
            atualizado = Usuario.atualizar_perfil(**kwargs_update)
        except ValueError as erro:
            flash(str(erro))
            usuario_form = dict(usuario)
            usuario_form["nome"] = nome
            return render_template("perfil.html", u=usuario_form), 400

        if eh_proprio:
            session["usuario_nome"] = atualizado["nome"]
            session["usuario_foto_id"] = atualizado.get("foto_arquivo_id")

        flash("Usuário atualizado com sucesso!")
        if eh_admin and not eh_proprio:
            return redirect(url_for("usuario.listar"))
        return redirect(url_for("formulario.index"))

    return render_template("perfil.html", u=usuario)


@usuario_bp.route("/usuarios/<int:id>/promover", methods=["POST"])
@admin_required
def promover(id: int):
    try:
        atualizado = Usuario.atualizar_funcao(id, "Admin")
        if atualizado:
            flash("Usuário promovido para Admin com sucesso!")
        else:
            flash("Usuário não encontrado.")
    except ValueError as erro:
        flash(str(erro))

    return redirect(url_for("usuario.listar"))


@usuario_bp.route("/usuarios/<int:id>/inativar", methods=["POST"])
@admin_required
def inativar(id: int):
    if int(session.get("usuario_id", 0)) == id:
        flash("Você não pode inativar sua própria conta.")
        return redirect(url_for("usuario.listar"))

    novo_status_str = request.form.get("ativo", "0").strip().lower()
    novo_ativo = novo_status_str in ("1", "true", "sim")

    atualizado = Usuario.definir_ativo(id, novo_ativo)
    if atualizado:
        acao = "ativado" if novo_ativo else "inativado"
        flash(f"Usuário {acao} com sucesso!")
    else:
        flash("Usuário não encontrado.")

    return redirect(url_for("usuario.listar"))
