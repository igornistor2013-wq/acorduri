@echo off
chcp 65001 >nul
setlocal
REM ===================================================================
REM  Colectarea zilnica a acordurilor de pe legis.md, de pe calculatorul
REM  tau. Optional: actualizare completa din legis.md (pornire manuala).
REM
REM  Ce face: git pull -> cauta actele noi din anul curent pe legis.md ->
REM  le clasifica -> reconstruieste legis_acorduri.html -> daca a gasit
REM  ceva nou: git commit + git push (site-ul se actualizeaza singur).
REM
REM  Se deschide o fereastra de Microsoft Edge pe legis.md. Daca apare
REM  bifa "nu sunt robot", bifeaz-o (ai 5 minute). Scriptul nu o ocoleste.
REM ===================================================================

cd /d "%~dp0"
set JURNAL=%~dp0legis_local.log
echo. >> "%JURNAL%"
echo ===== %date% %time% ===== >> "%JURNAL%"

REM Python: preferam lansatorul "py" (instalarea standard din Windows)
set PY=python
where py >nul 2>&1 && set PY=py -3

echo [1/4] Aduc ultima versiune de pe GitHub...
git pull --rebase origin main >> "%JURNAL%" 2>&1 || goto :eroare_git

echo [2/4] Caut acte noi pe legis.md (se deschide o fereastra de browser)...
%PY% legis_watch.py --headed --profil .legis_profil --browser msedge
set COD=%errorlevel%
if "%COD%"=="3" goto :blocat
if not "%COD%"=="0" goto :eroare

REM Sumele acordurilor: citim textul integral (PDF) al fiecarui act nou, in
REM aceeasi fereastra. Prima rulare are ~1300 de acte de citit; se opreste dupa
REM 20 de minute si continua la rularea urmatoare. Un esec aici nu opreste
REM publicarea actelor noi.
echo [3/4] Citesc sumele din textele actelor (prima data dureaza mai mult)...
%PY% -m pip install --quiet --disable-pip-version-check pypdf pypdfium2 pytesseract >> "%JURNAL%" 2>&1
%PY% legis_sume.py --headed --profil .legis_profil --browser msedge --limita-min 20
set COD=%errorlevel%
if "%COD%"=="3" (echo Cloudflare a cerut din nou verificarea; sumele se citesc data viitoare. & echo sume: blocat >> "%JURNAL%")
if not "%COD%"=="0" if not "%COD%"=="3" (echo Citirea sumelor a esuat, cod %COD%. Continui fara ele. & echo sume: eroare cod %COD% >> "%JURNAL%")
REM Acordurile atasate la acte (PDF-urile din fisa actului pe legis.md): acolo sta
REM suma de cele mai multe ori. PDF-urile scanate se citesc cu OCR, daca programul
REM Tesseract e instalat. Se opreste dupa 20 de minute si continua data viitoare.
echo       Citesc acordurile atasate la acte...
%PY% legis_atasamente.py --headed --profil .legis_profil --browser msedge --limita-min 20
set COD=%errorlevel%
if "%COD%"=="3" (echo Cloudflare a cerut din nou verificarea; atasamentele se citesc data viitoare. & echo atasamente: blocat >> "%JURNAL%")
if not "%COD%"=="0" if not "%COD%"=="3" (echo Citirea atasamentelor a esuat, cod %COD%. Continui fara ele. & echo atasamente: eroare cod %COD% >> "%JURNAL%")
%PY% legis_pagina.py >> "%JURNAL%" 2>&1

echo [4/4] Public pe GitHub, daca e ceva nou...
REM git status vede si fisierul de sume la prima lui aparitie (git diff nu vede fisierele noi)
set SCHIMBAT=
for /f "delims=" %%i in ('git status --porcelain -- legis_brut.json date/legis_sume.json') do set SCHIMBAT=1
if not defined SCHIMBAT (echo Nimic nou pe legis.md azi. & echo nimic nou >> "%JURNAL%" & goto :gata)
git add legis_brut.json legis_acorduri.html raport_legis.md jurnal_legis.md
REM separat: daca fisierul de sume lipseste, un singur "git add" ar esua cu totul
if exist "date\legis_sume.json" git add date/legis_sume.json
git commit -m "legis.md: acte noi (local) - %date%" >> "%JURNAL%" 2>&1
git push >> "%JURNAL%" 2>&1 || (git pull --rebase origin main >> "%JURNAL%" 2>&1 & git push >> "%JURNAL%" 2>&1) || goto :eroare_git
echo Publicat pe GitHub. Vezi raport_legis.md pentru lista.
echo publicat >> "%JURNAL%"
goto :gata

:blocat
echo.
echo Cloudflare a cerut bifa "nu sunt robot" si nu a fost bifata in 5 minute.
echo Porneste din nou legis_local.bat si bifeaza in fereastra care se deschide.
echo blocat de Cloudflare >> "%JURNAL%"
timeout /t 60
exit /b 3

:eroare_git
echo.
echo Git nu a putut comunica cu GitHub (detalii in legis_local.log).
echo Daca e prima rulare, poate trebuie sa te autentifici: ruleaza o data
echo "git push" in acest folder si urmeaza fereastra de login GitHub.
echo eroare git >> "%JURNAL%"
timeout /t 120
exit /b 1

:eroare
echo.
echo Verificarea a esuat (cod %COD%). Citeste mesajul de mai sus.
echo eroare cod %COD% >> "%JURNAL%"
timeout /t 120
exit /b 1

:gata
timeout /t 10
exit /b 0
