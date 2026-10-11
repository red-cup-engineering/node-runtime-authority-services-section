(defun suros-render-object-as-html-homepage (object)
  (ht-set! (ht-get object :headers) "Content-type" "text/html")
  (let ((data (ht-get object :datapool)))
    (ht-set!
     object :rendering
     (concat
      (suros-render-html-document-declaration object)
      "<body><header>" (suros-render-html-h1 object) "</header>"
      "<p>" (ht-get data "server-name") " is "
      (ht-get data "server-description") "."
      (let ((link (ht-get data "server-source-link")))
	(if link
	    (concat " Its source is available at "
	     "<a href=\"" link  "\">" link "</a>.")))
      "</p></body></html>"))))
