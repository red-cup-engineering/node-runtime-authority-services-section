(setq ems-dict
      '(("banana"
         ("definition" . "an elongated berry, technically")
         ("sources"
          ("Wikipedia" . "https://en.wikipedia.org/wiki/Banana")
          ("Wiktionary" . "https://en.wiktionary.org/wiki/banana")))))
(defun ems-get-def
    (term)
  "Return the definition of TERM from ems-dict."
  (cdr (assoc "definition" (cdr (assoc term ems-dict)))))
(defun ems-cap-first-char
    (&optional string)
  "Return STRING with the first character capitalized."
  (when (and string (> (length string) 0))
    (let ((first-char (substring string nil 1))
          (rest-str (substring string 1)))
      (concat (capitalize first-char) rest-str))))
