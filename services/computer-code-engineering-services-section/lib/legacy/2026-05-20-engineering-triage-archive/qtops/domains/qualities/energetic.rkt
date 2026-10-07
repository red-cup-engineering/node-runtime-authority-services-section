#lang racket

(provide <>energetic
         >>make-energy-procedures
         >energy
         >set-energy!
         >increment-energy!)

(define ((>energy t)) 0)
(define ((>set-energy! t) m)
  (when (< m 0) (set! m 0))
  (t 'set-procedure! 'energy (λ () m)))
(define ((>increment-energy! t) [m 1])
  (t 'set-energy! (+ (t 'energy) m)))

(define (>>make-energy-procedures t)
  (list
   (cons 'energy (>energy t))
   (cons 'set-energy! (>set-energy! t))
   (cons 'increment-energy! (>increment-energy! t))))

(define (<>energetic t)
  (t 'set-procedures! (>>make-energy-procedures t)))
