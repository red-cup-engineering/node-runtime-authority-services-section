#lang racket

(provide <>universe-thing
         >>make-universe-thing-procedures
         >universe
         >set-universe!)

(define ((>universe t))
  (void))
(define ((>set-universe! t) u)
  (t 'set-procedure! 'universe (λ () u)))

(define (>>make-universe-thing-procedures t)
  (list
   (cons 'universe (>universe t))
   (cons 'set-universe! (>set-universe! t))))

(define (<>universe-thing t)
  (t 'set-procedures! (>>make-universe-thing-procedures t))
  t)
