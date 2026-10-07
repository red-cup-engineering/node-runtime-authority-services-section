#lang racket

(require qtops
         "../../qualities/document.rkt")

(provide <>hello-world)

(define (<>hello-world t)
  (<>document
   t #:name "Hello World"
   #:content "This is a thing-based hello-world document that lives in its own file."))
