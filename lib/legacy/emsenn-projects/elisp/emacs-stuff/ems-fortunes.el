(setq ems-fortunes
'("Rome wasn't built in a day and you shouldn't aspire for your mind to be any less."
"Our society is not sustained by mortar and stone."))
(defun ems-insert-fortune ()
"Inserts a random fortune at point in the current buffer."
(interactive)
 (insert (seq-random-elt ems-fortunes)))
