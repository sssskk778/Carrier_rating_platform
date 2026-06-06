from functools import wraps
from flask import session, redirect, url_for, jsonify, request
from src import db
from src.models import User


class Roles:
    ADMIN = 'admin'
    USER = 'user'


def current_user():
    uid = session.get('user_id')
    return db.session.get(User, uid) if uid else None


def _is_api_request():
    """Проверяет что запрос идёт к API а не к веб-странице."""
    return request.path.startswith('/api/')


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            if _is_api_request():
                return jsonify({'ok': False, 'error': 'Необходима авторизация'}), 401
            return redirect(url_for('auth.login'))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        user = current_user()
        if not user:
            if _is_api_request():
                return jsonify({'ok': False, 'error': 'Необходима авторизация'}), 401
            return redirect(url_for('auth.login'))
        if user.role != Roles.ADMIN:
            if _is_api_request():
                return jsonify({'ok': False, 'error': 'Нет доступа'}), 403
            from flask import abort
            abort(403)
        return view(*args, **kwargs)
    return wrapped