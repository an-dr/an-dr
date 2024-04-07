# pandoc -f gfm -t html5 --metadata pagetitle="cv.md" --css styles.css  cv.md -o cv.pdf

# pandoc -s -f markdown -t html5 -o cv.html cv.md -c style.css

pandoc README.md -o README.pdf "-fmarkdown-implicit_figures -o" --from=markdown -V geometry:margin=.3in --toc --highlight-style=espresso

