from flask import Blueprint, flash, redirect, render_template, request, session, url_for
from werkzeug.utils import secure_filename
from models.usuario import Usuario

auth_bp = Blueprint("auth", __name__)

EXTENSOES_IMAGEM = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _ler_foto_opcional(arquivo_foto) -> tuple[str, str, bytes] | None:
    if not arquivo_foto or not arquivo_foto.filename:
        return None

    nome_seguro = secure_filename(arquivo_foto.filename)
    ext = ""
    if "." in nome_seguro:
        ext = "." + nome_seguro.rsplit(".", 1)[1].lower()

    if ext not in EXTENSOES_IMAGEM:
        raise ValueError(
            "A foto deve ser uma imagem válida (.jpg, .jpeg, .png, .webp ou .gif)."
        )

    dados = arquivo_foto.read()
    if not dados:
        raise ValueError("O arquivo de imagem enviado está vazio.")

    return nome_seguro, EXTENSOES_IMAGEM[ext], dados


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
        session["usuario_foto_id"] = usuario.get("foto_arquivo_id")
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
            foto = _ler_foto_opcional(request.files.get("foto"))
            Usuario.criar(nome=nome, email=email, senha=senha, foto=foto)
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
