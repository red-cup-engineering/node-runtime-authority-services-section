#lang racket

(provide <>region-area
         >>make-region-area-procedures
         >region
         >set-region!)

(define ((>region t))
  (void))
(define ((>set-region! t) u)
  (t 'set-procedure! 'region (λ () u)))

(define (>>make-region-area-procedures t)
  (list
   (cons 'region (>region t))
   (cons 'set-region! (>set-region! t))))

(define (<>region-area t)
  (t 'set-procedures! (>>make-region-area-procedures t))
  t)
