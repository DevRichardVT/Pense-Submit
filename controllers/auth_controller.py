from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from models.usuario import Usuario

auth_bp = Blueprint("auth", __name__)


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get("usuario_id"):
        return redirect(url_for("formulario.index"))

    if request.method == "POST":
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")

        if not email or not senha:
            flash("Preencha e-mail e senha.")
            return render_template("login.html"), 400

        usuario = Usuario.autenticar(email, senha)
        if not usuario:
            flash("E-mail ou senha inválidos.")
            return render_template("login.html"), 401

        session.clear()
        session["usuario_id"] = usuario["id"]
        session["usuario_nome"] = usuario["nome"]
        session["usuario_email"] = usuario["email"]
        session["usuario_funcao"] = usuario["funcao"]
        flash(f"Bem-vindo(a), {usuario['nome']}!")
        return redirect(url_for("formulario.index"))

    return render_template("login.html")


@auth_bp.route("/cadastro", methods=["GET", "POST"])
def cadastro():
    if session.get("usuario_id"):
        return redirect(url_for("formulario.index"))

    if request.method == "POST":
        nome = request.form.get("nome", "").strip()
        email = request.form.get("email", "").strip()
        senha = request.form.get("senha", "")

        try:
            Usuario.criar(nome=nome, email=email, senha=senha)
        except ValueError as erro:
            flash(str(erro))
            return render_template("cadastro.html"), 400

        flash("Cadastro realizado com sucesso! Faça seu login.")
        return redirect(url_for("auth.login"))

    return render_template("cadastro.html")


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    session.clear()
    flash("Você saiu da sua conta.")
    return redirect(url_for("auth.login"))
