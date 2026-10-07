#lang racket

(require "../utilities/lists.rkt")

(provide make-trivia-mudsocket-commands)

(define ((make-trivia-mudsocket-command t) a)
  (if (and (t 'has-procedure? 'container)
           (procedure? (t 'container)))
      (if ((t 'container) 'has-procedure? 'trivia)
          (t 'message! (random-element ((t 'container) 'trivia)))
          (t 'message! "This area doesn't have any trivia."))
      (t "This isn't trivial, but you aren't anyplace.")))

(define (make-trivia-mudsocket-commands t)
  (list
   (cons "trivia" (make-trivia-mudsocket-command t))))
