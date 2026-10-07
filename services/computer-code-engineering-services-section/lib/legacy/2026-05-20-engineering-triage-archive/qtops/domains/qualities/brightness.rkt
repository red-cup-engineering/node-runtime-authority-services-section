#lang racket

(provide <>light
         >>make-brightness-procedures
         >brightness
         >set-brightness!
         >increment-brightness!)

(define ((>brightness t)) 0)
(define ((>set-brightness! t) m)
  (when (< m 0) (set! m 0))
  (t 'set-procedure! 'brightness (λ () m)))
(define ((>increment-brightness! t) [m 1])
  (t 'set-brightness! (+ (t 'brightness) m)))

(define (>>make-brightness-procedures t)
  (list
   (cons 'brightness (>brightness t))
   (cons 'set-brightness! (>set-brightness! t))
   (cons 'increment-brightness! (>increment-brightness! t))))

(define (<>light t)
  (t 'set-procedures! (>>make-brightness-procedures t))
  t)
