#lang racket

(require qtops
         "../../qualities/document.rkt")

(provide <>contact)

(define (<>contact t)
  (<>document
   t #:name "Contact emsenn"
   #:content
   `(section
     (ul
      (li (bold (em "In a hurry?"))
          (ul (li "Email "
                  (a ((href "mailto:emsenn@emsenn.net"))
                     "emsenn@emsenn.net"))))
      (li (bold (em "Representing a government?"))
          (ul (li "Check "
                  (a ((href "/docs/legal-disclosures"))
                     "/docs/legal-disclosures"))))
      (li (bold (em "Want to send me money or mail?"))
          (ul (li "Check "
                  (a ((href "/docs/support"))
                     "docs/support")))))
     (p "Other means of contact:")
     (ul
      (li "ActivityPub"
          (ul
           (li (a ((href "https://ecosteader.com/@emsenn"))
                  "ActivityPub"))))
      (li "Matrix"
          (ul
           (li "@emsenn:matrix.org")))))))
