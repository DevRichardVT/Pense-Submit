from flask import Blueprint
from controllers.decorators import login_required

formulario_bp = Blueprint("formulario", __name__)


@formulario_bp.route("/")
@login_required
def index():
    return ""


@formulario_bp.route("/formulario", methods=["GET", "POST"])
@login_required
def criar():
    return ""
