(defun ems-read-something
    ()
  "Return a random element's cdr, which should be a string that is a URL, from the ems-reading-list variable."
  (cdr (assoc 'source (cdr (seq-random-elt (cdr (assoc 'pending ems-reading-log)))))))
(defun ems-read-something-now ()
  "Opens a random item from the pending reading list."
  (interactive) (browse-url (ems-read-something)))
(defun ems-plan-to-read
    (tit auth src)
  "Adds an item to my reading list"
  (interactive "sTitle? \nsAuthor? \nsSource? ")
  (push
   (cons tit (cons (cons 'author auth) (list (cons 'source src))))
   (cdr (assoc 'pending ems-reading-log))))
