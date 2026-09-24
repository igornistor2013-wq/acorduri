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

echo [1/3] Aduc ultima versiune de pe GitHub...
git pull --rebase origin main >> "%JURNAL%" 2>&1 || goto :eroare_git

echo [2/3] Caut acte noi pe legis.md (se deschide o fereastra de browser)...
%PY% legis_watch.py --headed --profil .legis_profil --browser msedge
set COD=%errorlevel%
if "%COD%"=="3" goto :blocat
if not "%COD%"=="0" goto :eroare

echo [3/3] Public pe GitHub, daca e ceva nou...
git diff --quiet -- legis_brut.json && (echo Nimic nou pe legis.md azi. & echo nimic nou >> "%JURNAL%" & goto :gata)
git add legis_brut.json legis_acorduri.html raport_legis.md jurnal_legis.md
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
