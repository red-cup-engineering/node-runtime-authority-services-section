(defun suros-render-headers-as-html-dl (object)
  (concat
   "<dl><dt>"
   (string-join
    (ht-map
     (lambda (key val)
       (concat key "</dt><dd>" val))
     (ht-get object :headers)) "</dd><dt>")
   "</dd></dl>"))
