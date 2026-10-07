#lang racket

(provide <>massive
         >>make-mass-procedures
         >mass
         >set-mass!
         >increment-mass!)

(define ((>mass t)) 0)
(define ((>set-mass! t) m)
  (when (< m 0) (set! m 0))
  (t 'set-procedure! 'mass (λ () m)))
(define ((>increment-mass! t) [m 1])
  (t 'set-mass! (+ (t 'mass) m)))

(define (>>make-mass-procedures t)
  (list
   (cons 'mass (>mass t))
   (cons 'set-mass! (>set-mass! t))
   (cons 'increment-mass! (>increment-mass! t))))

(define (<>massive t)
  (t 'set-procedures! (>>make-mass-procedures t))
  t)
