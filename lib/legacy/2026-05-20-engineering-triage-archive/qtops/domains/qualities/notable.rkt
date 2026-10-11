#lang racket

(provide <>notable
         >>make-notable-procedures
         >notable?
         >set-notable!)

(define ((>notable? t)) #t)
(define ((>set-notable! t) n)
      (t 'set-procedure! 'notable (λ () n)))

(define (>>make-notable-procedures t)
  (list
   (cons 'notable? (>notable? t))
   (cons 'set-notable! (>set-notable! t))))

(define (<>notable t)
  (t 'set-procedures! (>>make-notable-procedures t))
  t)
