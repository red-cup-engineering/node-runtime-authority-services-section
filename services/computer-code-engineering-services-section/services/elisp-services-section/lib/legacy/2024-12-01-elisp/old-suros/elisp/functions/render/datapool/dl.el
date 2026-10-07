(defun suros-render-object-datapool-as-html-dl (object)
  (concat
   "<dl><dt>"
   (string-join
    (ht-map
     (lambda (key val)
       (concat key "</dt><dd>" val))
     (ht-get object :datapool)) "</dd><dt>")
   "</dd></dl>"))
