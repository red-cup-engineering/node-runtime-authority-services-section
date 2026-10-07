#+TITLE: emsenn's Fortunes
#+EXPORT_FILE_NAME: ems-fortunes
#+HUGO_BASE_DIR: ~/dev/personal-website/
#+HUGO_SECTION: computer-instruction-sets
* emsenn's Fortunes
#+begin_src elisp
(setq ems-fortunes
'("Rome wasn't built in a day and you shouldn't aspire for your mind to be any less."
  "Our society is not sustained by mortar and stone."
  "Our mouths were made for praising that sweet by-and-by."
  "Here's to my sweethearts, and here's to my friends. Here's to our means, and here's to our ends."))
(defun ems-insert-fortune ()
"Inserts a random fortune at point in the current buffer."
(interactive)
 (insert (seq-random-elt ems-fortunes)))
#+end_src
