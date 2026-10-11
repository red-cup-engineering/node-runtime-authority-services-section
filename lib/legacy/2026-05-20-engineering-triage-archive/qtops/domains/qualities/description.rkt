#lang racket

(provide <>described
         >>make-description-procedures
         >description
         >set-description!)


(define ((>description t)) "This is a thing.")
(define ((>set-description! t) n)
  (if (string? n)
      (t 'set-procedure! 'description (λ () n))
      (t 'set-procedure! 'description n)))

(define (>>make-description-procedures t)
  (list
   (cons 'description (>description t))
   (cons 'set-description! (>set-description! t))))

(define (<>described t #:description [description #f])
  (unless (t 'has-procedure? 'description)
    (t 'set-procedures! (>>make-description-procedures t)))
  (when description (t 'set-description! description))
  t)
