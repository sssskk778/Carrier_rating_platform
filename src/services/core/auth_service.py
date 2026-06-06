"""
Сервис аутентификации пользователей.

Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
from src import db
from src.models import User
from src.repositories import UserRepository


class AuthService:
    """
    Аутентификация пользователей: вход и регистрация.
    Атрибуты:
        users — репозиторий пользователей.
    Методы:
        login    — проверка учётных данных и вход в систему.
        register — создание нового пользователя.
    """

    def __init__(self):
        self.users = UserRepository()

    def login(self, username: str, password: str) -> User:
        user = self.users.get_by_username(username)
        if not user or not user.check_password(password):
            raise ValueError('Неверное имя пользователя или пароль')
        return user

    def register(self, username: str, password: str, full_name: str) -> User:
        if self.users.get_by_username(username):
            raise ValueError('Пользователь с таким логином уже существует')
        user = User(username=username, full_name=full_name, role='user')
        user.set_password(password)
        self.users.save(user)
        db.session.commit()
        return user