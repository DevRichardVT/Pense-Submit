import os
import uuid

from flask import Flask, abort, flash, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")

# Na Vercel só é possível escrever em /tmp
if os.environ.get("VERCEL"):
    app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
else:
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # limite real da Vercel (~4,5 MB)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Na Vercel só é possível escrever em /tmp
if os.environ.get("VERCEL"):
    app.config["UPLOAD_FOLDER"] = "/tmp/uploads"
else:
    app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 4 * 1024 * 1024  # limite real da Vercel (~4,5 MB)
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# Pasta onde os PDFs enviados serão salvos (dentro de static/ para poderem ser abertos pelo navegador)
app.config["UPLOAD_FOLDER"] = os.path.join(app.root_path, "static", "uploads")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # limite de 10 MB
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

MODALIDADES = ["Ensino", "Pesquisa", "Extensão"]

# lista global
trabalhos = [
    {
        "titulo": "Teoria Quântica",
        "autor": "Fulano",
        "campus": "IFRS - Campus Farroupilha",
        "modalidade": "Pesquisa",
        "resumo": "Lorem ipsum dolor sit amet, consectetur adipiscing elit, sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris nisi ut aliquip ex ea commodo consequat.",
        "arquivo": None,
    },
    {
        "titulo": "Horta Escolar Sustentável",
        "autor": "Beltrana",
        "campus": "IFRS - Campus Bento Gonçalves",
        "modalidade": "Extensão",
        "resumo": "Projeto de extensão que envolve a comunidade escolar na criação e manutenção de uma horta, com oficinas sobre alimentação saudável e compostagem.",
        "arquivo": None,
    },
    {
        "titulo": "Metodologias Ativas no Ensino Técnico",
        "autor": "Ciclano",
        "campus": "IFRS - Campus Caxias do Sul",
        "modalidade": "Ensino",
        "resumo": "Relato de experiência sobre a aplicação de aprendizagem baseada em projetos em turmas do curso técnico integrado.",
        "arquivo": None,
    },
]

def salvar_pdf(arquivo):
    """Salva o PDF enviado e devolve o nome salvo (ou None se não houver arquivo)."""
    if not arquivo or arquivo.filename == "":
        return None
    nome_original = secure_filename(arquivo.filename)
    if not nome_original.lower().endswith(".pdf"):
        raise ValueError("O arquivo precisa ser um PDF.")
    nome_final = f"{uuid.uuid4().hex[:8]}_{nome_original}"
    arquivo.save(os.path.join(app.config["UPLOAD_FOLDER"], nome_final))
    return nome_final

@app.route("/")
def index():
    return render_template("index.html", trabalhos=trabalhos)

@app.route("/formulario", methods=["GET", "POST"])
def formulario():
    if request.method == "POST":
        titulo = request.form.get("titulo", "").strip()
        autor = request.form.get("autor", "").strip()
        campus = request.form.get("campus", "").strip()
        resumo = request.form.get("resumo", "").strip()
        modalidade = request.form.get("modalidade", "")
 
        if not (titulo and autor and campus and resumo) or modalidade not in MODALIDADES:
            flash("Preencha todos os campos e escolha uma modalidade válida.")
            return render_template("formulario.html", modalidades=MODALIDADES), 400

        try:
            nome_arquivo = salvar_pdf(request.files.get("arquivo"))
        except ValueError as erro:
            flash(str(erro))
            return render_template("formulario.html", modalidades=MODALIDADES), 400

        trabalhos.append(
            {
                "titulo": titulo,
                "autor": autor,
                "campus": campus,
                "resumo": resumo,
                "modalidade": modalidade,
                "arquivo": nome_arquivo,
            }
        )
        flash("Trabalho enviado com sucesso!")
        return redirect(url_for("index"))

    return render_template("formulario.html", modalidades=MODALIDADES)

@app.route("/trabalho/<int:id>")
def detalhe(id):
    if id < 0 or id >= len(trabalhos):
        abort(404)
    return render_template("detalhe.html", t=trabalhos[id])

@app.errorhandler(413)
def arquivo_grande(_erro):
    flash("Arquivo muito grande (máximo de 10 MB).")
    return redirect(url_for("formulario"))

if __name__ == "__main__":
    app.run(debug=True)