"""
Сервис аутентификации пользователей.
"""
from src import db
from src.models import User
from src.repositories import UserRepository


class AuthService:

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
