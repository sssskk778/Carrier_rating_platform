"""
Расширения приложения — хранит экземпляры celery и других расширений.
"""
from celery import Celery

celery = Celery()