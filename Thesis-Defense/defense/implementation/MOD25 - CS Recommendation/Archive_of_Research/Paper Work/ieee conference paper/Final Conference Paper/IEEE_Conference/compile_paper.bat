@echo off
echo Cleaning old files...
del *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot *.acn *.acr *.alg *.glg *.glo *.gls *.ist

echo Running Pass 1 (pdflatex)...
pdflatex -interaction=nonstopmode "Charging Station Recommendation Framework.tex"

echo Skipping Bibliography (hardcoded in tex)...
rem bibtex "Charging Station Recommendation Framework"

echo Running Pass 2 (pdflatex)...
pdflatex -interaction=nonstopmode "Charging Station Recommendation Framework.tex"

echo Running Pass 3 (pdflatex)...
pdflatex -interaction=nonstopmode "Charging Station Recommendation Framework.tex"

echo Compilation Complete!
pause
