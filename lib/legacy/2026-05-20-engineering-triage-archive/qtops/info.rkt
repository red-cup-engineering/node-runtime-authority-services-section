#lang info

(define collection "qtops")

(define pkg-desc
  "Perform operations on things with qualities")
(define version "0.5.0")
(define pkg-authors '("emsenn"))
(define scribblings '(("scribblings/qtops.scrbl" (multi-page))))
(define deps '("base"
               "rackunit-lib"))
(define build-deps '("racket-doc"
                     "scribble-lib"))
