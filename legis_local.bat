@echo off
REM Verificarea legis.md rulata de pe calculatorul tau, in loc de GitHub.
REM Foloseste-o daca workflow-ul "Verifica legis.md" e blocat de Cloudflare.
REM
REM Prima data: dublu-click. Se deschide o fereastra de browser pe legis.md;
REM daca apare bifa "nu sunt robot", bifeaz-o (ai 5 minute). Profilul din
REM .legis_profil pastreaza cookie-ul, deci rularile urmatoare trec singure.
REM
REM Zilnic: Task Scheduler (Planificator de activitati) -> Creare activitate
REM de baza -> Zilnic -> Pornire program -> acest fisier.

cd /d "%~dp0"
git pull --rebase origin main || goto :eroare
python legis_watch.py --headed --profil .legis_profil
if errorlevel 1 goto :eroare

git diff --quiet -- legis_brut.json && (echo Nimic nou. & goto :gata)
git add legis_brut.json legis_acorduri.html raport_legis.md jurnal_legis.md
git commit -m "legis.md: acte noi (local)"
git push || goto :eroare
echo Publicat.
goto :gata

:eroare
echo.
echo Rularea a esuat. Citeste mesajul de mai sus.
pause
exit /b 1

:gata
exit /b 0
