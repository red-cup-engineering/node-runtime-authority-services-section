(defun suros-render-html-h1 (object)
  (concat
   "<h1>"
   (ht-get (ht-get object :datapool) "object-title")
   "</h1>"))
