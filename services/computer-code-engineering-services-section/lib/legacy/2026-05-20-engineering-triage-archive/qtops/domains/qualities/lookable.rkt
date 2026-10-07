#lang racket

(require "description.rkt"
         "noun.rkt")

(provide <>lookable)

(define (<>lookable t
                    #:name [name #f]
                    #:description [description #f]
                    #:nouns [nouns #f]
                    #:adjectives [adjectives #f])
  (when name (t 'set-name! name))
  (<>described
   (<>noun
    t #:nouns nouns #:adjectives adjectives)
   #:description description))
