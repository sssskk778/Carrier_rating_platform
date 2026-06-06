"""
Запуск приложения
Автор: Лосева Е.А.
Дата создания: 13.03.2026
Последнее изменение: 01.06.2026
Контакт: ekaterinaloseva91@gmail.com
"""
from src import create_app
app = create_app()
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)
