#lang racket

(require "../../qualities/library.rkt"
         "about-emsops.rkt"
         "contact.rkt"
         "hello-world.rkt"
         "legal-disclosures.rkt"
         "support.rkt")

(provide website-library-listing)

(define website-library-listing
  `((about-emsops ,<>about-emsops)
    (contact ,<>contact)
    (hello-world ,<>hello-world)
    (legal-disclosures ,<>legal-disclosures)
    (support ,<>support)))
