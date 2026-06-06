from flask import Blueprint, render_template, redirect, url_for, session, jsonify

auth_bp = Blueprint('auth', __name__)


@auth_bp.get('/login')
def login():
    if session.get('user_id'):
        return redirect(url_for('web.index'))
    return render_template('login.html')


@auth_bp.get('/register')
def register():
    if session.get('user_id'):
        return redirect(url_for('web.index'))
    return render_template('register.html')


@auth_bp.get('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('auth.login'))