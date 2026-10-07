#lang racket

(provide <>lit
         >>make-light-procedures)

(define ((>light t)) 0)
(define ((>set-light! t) m)
  (when (< m 0) (set! m 0))
  (t 'set-procedure! 'light (λ () m)))
(define ((>increment-light! t) [m 1])
  (t 'set-light! (+ (t 'light) m)))

(define (>>make-light-procedures t)
  (list
   (cons 'light (>light t))
   (cons 'set-light! (>set-light! t))
   (cons 'increment-light! (>increment-light! t))))

(define (<>lit t)
  (t 'set-procedures! (>>make-light-procedures t))
  t)
