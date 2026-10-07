#lang racket

(provide <>exitable
         >>make-exit-procedures
         >exits
         >has-exit?
         >exit
         >set-exits!)

(define (>exits t)
  (define real-exits (make-hash))
  (λ () real-exits))
(define ((>has-exit? t) k)
  (hash-has-key? (t 'exits) k))
(define ((>exit t) k)
  (hash-ref (t 'exits) k))
(define ((>set-exits! t) E)
  (map
   (λ (e)
     (hash-set! (t 'exits)
                (if (string? (car e))
                    (string->symbol (car e))
                    (car e))
                (cdr e)))
   E))
(define ((>set-exit! t) k e)
  (t 'set-exits! (list (cons k e))))

(define (>>make-exit-procedures t)
  (list
   (cons 'exits (>exits t))
   (cons 'has-exit? (>has-exit? t))
   (cons 'exit (>exit t))
   (cons 'set-exits! (>set-exits! t))
   (cons 'set-exit! (>set-exit! t))))

(define (<>exitable t)
  (t 'set-procedures! (>>make-exit-procedures t))
  t)
