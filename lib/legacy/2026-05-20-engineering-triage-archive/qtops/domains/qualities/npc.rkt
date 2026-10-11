#lang racket

(require "description.rkt"
         "notable.rkt"
         "pronouns.rkt")


(provide <>npc)

(define (<>npc t
               #:name [name "someone"]
               #:description [description "This is someone."]
               #:pronouns [pronouns >>make-e-pronoun-procedures])
  (unless (t 'has-procedure? 'description)
    (t 'set-procedures! (>>make-description-procedures t)))
  (unless (t 'has-procedure? 'notable?)
    (t 'set-procedures! (>>make-notable-procedures t)))
  (t 'set-procedures! (pronouns t))
  (t 'set-name! name)
  (t 'set-description! description)
  t)
