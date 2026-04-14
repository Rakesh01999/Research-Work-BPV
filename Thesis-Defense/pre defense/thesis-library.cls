% thesis-library.cls - ASU Master's Thesis class
% Based on the provided Masters.sty file

\NeedsTeXFormat{LaTeX2e}
\ProvidesClass{thesis-library}[Master's Thesis class]

\LoadClass[12pt,a4paper]{report}

% Required packages
\usepackage[T1]{fontenc}
\usepackage{mathptmx}
\usepackage{titlesec}
\usepackage{graphicx}
\usepackage[acronym]{glossaries}
\usepackage{fmtcount}
\usepackage{lastpage}

\usepackage{fancyhdr}
%\usepackage{etoolbox}
\usepackage{setspace}

\usepackage{arabtex}
\usepackage{utf8}
\usepackage{geometry}


% Add the set space package and enable double spacing
\doublespacing


% Margins
\setlength{\headheight}{28.61798pt}
\setlength{\textwidth}{16cm}
\setlength{\textheight}{23cm}
\setlength{\oddsidemargin}{0.5cm}
\setlength{\evensidemargin}{0.5cm}
\setlength{\topmargin}{-1cm}


% Section headings
\titleformat{\chapter}[display]
{\normalfont\huge\bfseries\filcenter}{\chaptertitlename\ \thechapter}{20pt}{\Huge}


\titlespacing*{\chapter}{0pt}{-80pt}{40pt}
\titleformat{\section}
{\normalfont\Large\bfseries}{\thesection}{1em}{}
\titleformat{\subsection}
{\normalfont\large\bfseries}{\thesubsection}{1em}{}

% Table of contents
\renewcommand{\contentsname}{Table of Contents}
\setcounter{tocdepth}{2}
\setcounter{secnumdepth}{3}

% List of Abbreviations
\newcommand{\listofabbreviations}{
  \printglossary[type=\acronymtype, title=List of Abbreviations, toctitle=List of Abbreviations,nonumberlist]
}
\makeglossaries
\newcommand{\clearemptydoublepage}{
  \thispagestyle{empty}
  \mbox{}
}


% Document information
\newcommand{\universitylogo}{\includegraphics[width=3cm]{images/JUST_logo_transparent.png}}
\newcommand{\titleA}{\thesisTitle}
\newcommand{\titleB}{\subtitle}
\newcommand{\by}{\byLabel}
\newcommand{\authorname}{\studentName}
\newcommand{\authorsign}{\studentSign}
\newcommand{\supervisorsign}{\supervisorSign}
\newcommand{\cosupervisorsign}{\cosupervisorSign}
\newcommand{\authorid}{\studentID}
\newcommand{\authorregyear}{\studentRegYear}
\newcommand{\authoracayear}{\studentAcaYear}
\newcommand{\supervisor}{\supervisorLabel}
\newcommand{\supervisorNameStyle}{\supervisorName}
\newcommand{\supervisorDesigStyle}{\supervisorDesig}
\newcommand{\supervisorAffStyle}{\supervisorAff}
\newcommand{\cosupervisor}{\coSupervisorLabel}
\newcommand{\cosupervisorNameStyle}{\coSupervisorName}
\newcommand{\cosupervisorDesigStyle}{\cosupervisorDesig}
\newcommand{\cosupervisorAffStyle}{\cosupervisorAff}
\newcommand{\degreeLineA}{\degreeLineALabel}
\newcommand{\degreeLineB}{\degreeLineBLabel}
\newcommand{\major}{\majorName}
\newcommand{\faculty}{\facultyName}
\newcommand{\university}{\universityName}
\newcommand{\region}{\regionName}
\newcommand{\approvaltext}{\approvalText}
\newcommand{\degreeyear}{\degreeyearName}
\newcommand{\degreemonth}{\degreemonthName}


% Cover page
\newcommand{\makecoverpage}{
\newgeometry{left=2cm,right=2cm,top=2cm,bottom=-2cm}
\begin{titlepage}
\begin{center}
    %{\par\noindent\rule{\textwidth}{1pt}}\\[0.5cm]
    {\Large \textbf{\university}}\\[0.25cm]
    {\large \region}\\[0.25cm]
    {\universitylogo}\\[1cm] %0.5
    %Huge
    {\Large \textbf{\titleA}}\\[0.3cm]
    %{\Large \textbf{\titleB}}\\[0.75cm] %1.25
    {\large \textbf{\by}}\\[0.0cm]
    {\large \authorname}\\[0.1cm]  %0.75
    {\large \authorid}\\[0.0cm]  %0.75
    {\large \authorregyear}\\[0.0cm]  %0.75
    {\large \authoracayear}\\[0.5cm]  %0.75
    {\large \textbf{\supervisor}}\\[0.0cm]
    {\large \supervisorNameStyle}\\[0.0cm] %0.75
    {\large \supervisorDesigStyle}\\[0.0cm] %0.75 
    {\large \supervisorAffStyle}\\[0.5cm] %0.75    
    {\large \textbf{\cosupervisor}}\\[0.0cm]
    {\large \cosupervisorNameStyle}\\[0.0cm] %1.25
    {\large \cosupervisorDesigStyle}\\[0.0cm] %0.75 
    {\large \cosupervisorAffStyle}\\[0.5cm] %0.75 
    {\large \degreeLineA}\\[0.0cm]
    {\large \degreeLineB}\\[0.0cm]
    {\large \major}\\[0.0cm]
    {\large \textbf{\faculty}}\\[0.1cm] %1.25
    {\par\noindent\rule{\textwidth}{1pt}}\\[0.1cm]
    {\large \textbf{\degreemonth~\degreeyear}}
\end{center}
\end{titlepage}
\restoregeometry
}

% Approval page
 \newcommand{\makeapprovalpage}{
 \begin{titlepage}
 \begin{center}
 {\LARGE \university}\\[0.1cm]
 {\large \region}\\[1cm]
 {\universitylogo}\\[0.5cm]
 %{\Large \textbf{\titleA}}\\[0.3cm]
 {\approvaltext}\\[0.5cm]
 {\authorsign}\\[1cm]
 {\par\noindent\rule{0.5\textwidth}{1pt}}\\[0.0cm]
 {\authorname}\\[1cm]  %0.75

  {\supervisorsign}\\[1cm]
 {\par\noindent\rule{0.5\textwidth}{1pt}}\\[2cm]
 %{\supervisorNameStyle}\\[1cm]  %0.75

  {\cosupervisorsign}\\[1cm]
 {\par\noindent\rule{0.5\textwidth}{1pt}}\\[0.0cm]
 %{\cosupervisorNameStyle}\\[0.1cm]  %0.75

\end{center}
\end{titlepage}
 }

% Print Chapter Title
\newcommand{\printchaptertitle}[1]{
  \cleardoublepage
  \pagestyle{empty}
  \refstepcounter{chapter}
  \edef\currentchapternumber{\thechapter}
  \edef\currentchaptertitle{\chaptername\ \thechapter: #1}
  \vspace*{\fill}
  \begin{center}
    \huge\textbf{\chaptername\ \thechapter\\[1ex] #1}
  \end{center}
  \vspace*{\fill}
  \cleardoublepage
  \thispagestyle{firstcontentpage}
  \addcontentsline{toc}{chapter}{\chaptername\ \thechapter: #1}

  \pagestyle{fancy}
  \fancyhf{}
  %\cfoot{\thepage}
  \fancyfoot[C]{Page \thepage \hspace{1pt} of \pageref{LastPage}}
}

\fancypagestyle{firstcontentpage}{
  \fancyhf{}
  \lhead{\textbf{\Large \currentchaptertitle} \\\vspace{1.5pt}}
  %\cfoot{\thepage}
  \renewcommand{\headrulewidth}{0.2pt}
  \fancyfoot[C]{Page \thepage \hspace{1pt} of \pageref{LastPage}}
}


\fancypagestyle{fancy}{
  \fancyhf{}
  %\cfoot{\thepage}
  \renewcommand{\headrulewidth}{0.0pt}
 \fancyfoot[C]{Page \thepage \hspace{1pt} of \pageref{LastPage}}
}
