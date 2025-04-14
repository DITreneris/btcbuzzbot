@echo off
echo BTCBuzzBot Heroku Deployment
echo ===========================
echo.

REM Set Git executable path
set GIT_PATH="C:\Program Files\Git\cmd\git.exe"

REM Configure Git
%GIT_PATH% config --global user.email "dummy@example.com"
%GIT_PATH% config --global user.name "Deployment Script"

REM Add files
echo Adding files...
%GIT_PATH% add .

REM Commit changes
echo Committing changes...
%GIT_PATH% commit -m "Update web interface with modernized design"

REM Push to Heroku
echo Deploying to Heroku...
%GIT_PATH% push heroku master

echo.
echo Deployment complete!
echo.
echo Check your app at: https://btcbuzzbot-7c02c485f88e.herokuapp.com/ 