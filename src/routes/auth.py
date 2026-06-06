"""
Модуль Web маршрутов аутентификации

Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
from flask import Blueprint, render_template, redirect, url_for, session, jsonify

auth_bp = Blueprint('auth', __name__)

# Маршрут для отображения страницы входа
@auth_bp.get('/login')
def login():
    if session.get('user_id'):
        return redirect(url_for('web.index'))
    return render_template('login.html')

# Маршрут для отображения страницы регистрации
@auth_bp.get('/register')
def register():
    if session.get('user_id'):
        return redirect(url_for('web.index'))
    return render_template('register.html')

# Маршрут для выхода из системы
@auth_bp.get('/logout')
def logout():
    session.pop('user_id', None)
    return redirect(url_for('auth.login'))