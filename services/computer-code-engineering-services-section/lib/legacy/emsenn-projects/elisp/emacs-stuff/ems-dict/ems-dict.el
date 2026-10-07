#+TITLE: Emsenn's Dictionary
#+EXPORT_FILE_NAME: ems-dict
#+HUGO_BASE_DIR: ~/dev/personal-website/
#+HUGO_SECTION: computer-instruction-sets
#+HUGO_DRAFT:
* Ems-Dict
(setq ems-dict
'(("hugo-theme"
(definition . "A collection of resources for Hugo, a static website generator, providing layouts for templating the site's content.")
(source . "https://gohugo.io/themes/"))))
(defun ems-read-dict-definition
(term)
"Return the definition of TERM from ems-dict."
(cdr (assoc 'definition (ems-dict-read-term term))))
(defun ems-read-dict-source
(term)
"Return the source of TERM from ems-dict."
(cdr (assoc 'source (ems-dict-read-term term))))
(defun ems-dict-read-term
(term)
"Returns the TERM from my dictionary."
(cdr (assoc term ems-dict)))
