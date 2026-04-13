@echo off
echo Cleaning old files...
del *.aux *.bbl *.blg *.log *.out *.toc *.lof *.lot *.acn *.acr *.alg *.glg *.glo *.gls *.ist

echo Running Pass 1 (pdflatex)...
pdflatex -interaction=nonstopmode thesis.tex

echo Running Bibliography (bibtex)...
bibtex thesis

echo Running Pass 2 (pdflatex)...
pdflatex -interaction=nonstopmode thesis.tex

echo Running Pass 3 (pdflatex)...
pdflatex -interaction=nonstopmode thesis.tex

echo Compilation Complete!
pause
