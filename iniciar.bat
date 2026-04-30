@echo off
echo Iniciando Constru-Trans...
call venv\Scripts\activate.bat
python manage.py runserver
pause
