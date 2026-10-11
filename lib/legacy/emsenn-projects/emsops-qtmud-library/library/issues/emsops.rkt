#lang racket

#;(require qtops
         "../../qualities/issue-bank.rkt")

#;(provide <>emsops-issues)

#;(define (<>emsops-issues t)
  (<>issue-bank
   t #:name "emsOps Issues")
  (t 'add-issue!
     #:name "link library"
     #:brief "A way to store and reference links as libraries.")
  (t 'add-issue!
     #:name "log library"
     #:brief "A way to store and reference logs as docs within a library.")
  (t 'add-issue!
     #:name "ActivityPub interface")
  (t 'add-issue!
     #:name "RSS interface"
     #:description "For starters, generate /logs/index.rss")
  (t 'add-issue! #:name "IRC interface")
  (t 'add-issue! #:name "Okaga should be able to travel."
     #:brief "I should be able to have the Okaga travel between Teraum and my personal domain.")
  (t 'add-issue! #:name "Logging metadata"
     #:brief "Logs should at the least have the time they're recorded available: not possible if they're read in from files! So... this is the impetus (is that the right word?) for developing persistence... great...")
  (t 'add-issue! #:name "Document qtOps"
     #:brief "Document the main things file first, updating the examples, then go through each quality.")
  (t 'add-issue! #:name "Document emsOps"
     #:brief "These documents are mostly meant for myself, so I'm going to focus on documenting the qualities and customizations that've cropped up in my declarations.")
  (t 'add-issue! #:name "host emsOps docs with emsOps"))
