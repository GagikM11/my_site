import sys
import os

# Подключаем твой файл app.py
sys.path.insert(0, os.path.dirname(__file__))
from app import app as application
