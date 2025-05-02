@echo off
cd /d C:\Users\EIKON\Desktop\tributosmart

echo.
echo 🔄 Adicionando arquivos...
git add .

echo.
set /p MSG="ajusta visual e adiciona logo"

git commit -m "%MSG%"

echo.
echo ☁️ Enviando para o GitHub...
git push

pause
