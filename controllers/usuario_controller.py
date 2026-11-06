from flask import Blueprint, flash, redirect, render_template, url_for
from controllers.decorators import admin_required
from models.usuario import Usuario

usuario_bp = Blueprint("usuario", __name__)


@usuario_bp.route("/usuarios", methods=["GET"])
@admin_required
def listar():
    usuarios = Usuario.listar_todos()
    return render_template("usuarios.html", usuarios=usuarios)


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
