#lang racket

(require "../things.rkt")

(provide <>fillable
         >>make-fillable-procedures
         >fill-quality!)

(define ((>fill-quality! t) k c [sk #f] [sm #f] [ph #f])
  (map
   (λ (r)
     (define w
       ((λ () (cond [(t 'has-procedure? 'create-thing^!)
                     (t 'create-thing^!)]
                    [(t 'has-procedure? 'create-thing!)
                     (t 'create-thing!)]
                    [(t 'has-procedure? 'universe)
                     ((t 'universe) 'create-thing!)]
                    [else (create-thing)]))))
     (r w)
     (when sk
       (unless (w 'has-procedure? sk)
         (w 'set-procedures! (sm w))))
     (when ph (ph w))
     w)
   c))

(define (>>make-fillable-procedures t)
  (list
   (cons 'fill-quality! (>fill-quality! t))))

(define (<>fillable t)
  (t 'set-procedures! (>>make-fillable-procedures t)))
