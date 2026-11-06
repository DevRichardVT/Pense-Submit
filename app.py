import os
import sys
from flask import Flask, flash, redirect, url_for
import database
from controllers import auth_bp, formulario_bp, usuario_bp


def create_app(testing: bool = False) -> Flask:
    flask_app = Flask(__name__)
    flask_app.secret_key = os.environ.get("SECRET_KEY", "troque-esta-chave")
    flask_app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
    flask_app.config["TESTING"] = testing

    if not testing:
        try:
            database.init_db()
        except Exception as exc:
            flask_app.logger.warning("Aviso ao inicializar banco PostgreSQL: %s", exc)

    flask_app.register_blueprint(auth_bp)
    flask_app.register_blueprint(usuario_bp)
    flask_app.register_blueprint(formulario_bp)

    @flask_app.errorhandler(413)
    def arquivo_grande(_erro):
        flash("Arquivo muito grande (máximo de 10 MB).")
        return redirect(url_for("formulario.criar"))

    return flask_app


app = create_app(
    testing=os.environ.get("FLASK_TESTING") == "1" or "pytest" in sys.modules
)

if __name__ == "__main__":
    app.run(debug=True)
