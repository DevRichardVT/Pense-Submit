from functools import wraps
from flask import abort, flash, redirect, session, url_for


def login_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("usuario_id"):
            flash("Faça login para acessar o sistema.")
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)

    return wrapped_view


def admin_required(view):
    @wraps(view)
    def wrapped_view(*args, **kwargs):
        if not session.get("usuario_id"):
            flash("Faça login para acessar o sistema.")
            return redirect(url_for("auth.login"))
        if str(session.get("usuario_funcao", "")).lower() != "admin":
            abort(403)
        return view(*args, **kwargs)

    return wrapped_view
