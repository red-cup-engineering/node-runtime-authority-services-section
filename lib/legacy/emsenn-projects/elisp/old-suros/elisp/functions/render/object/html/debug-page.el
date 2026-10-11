(defun suros-make-debug-html-object (object)
  (ht-set! (ht-get object :headers) "Content-type" "text/html")
  (let ((data (ht-get object :datapool)))
  (ht-set!
   object :rendering
   (concat
    "<html><body>"
    "<h1>"(ht-get data "object-title")"</h1>"
    "<section><h2>Object Headers</h2>"
    (suros-render-headers-as-html-dl object)
    "</section>"
    "<section><h2>Object Datapool</h2>"
    (suros-render-datapool-as-html-dl object)
    "</body></html>"))))
