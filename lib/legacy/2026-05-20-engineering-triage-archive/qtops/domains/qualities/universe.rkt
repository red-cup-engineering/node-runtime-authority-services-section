#lang racket

(require "../things.rkt"
         "fillable.rkt"
         "universe-thing.rkt")

(provide <>universe
         >>make-universe-procedures)

(define ((>things t)) (list))

(define ((>set-things! t) C)
  (t 'set-procedure! 'things (λ () C)))

(define ((>add-thing! t) c)
  (t 'set-things! (append (t 'things) (list c))))

(define ((>remove-thing! t) c)
  (t 'set-things! (remove c (t 'things))))

(define ((>create-thing! t) [n "thing"])
  (define c (create-thing n))
  (c 'set-procedures! (>>make-universe-thing-procedures c))
  (c 'set-universe! t)
  (t 'add-thing! c)
  c)

(define ((>fill-things! t) T)
  (t 'fill-quality!
     'things T
     'universe >>make-universe-thing-procedures))

(define (>>make-universe-procedures t)
  (log-debug "Making universe procedures for ~a."
             (if (t 'has-procedure? 'name) (t 'name) t))
  (list
   (cons 'create-thing! (>create-thing! t))
   (cons 'things (>things t))
   (cons 'set-things! (>set-things! t))
   (cons 'add-thing! (>add-thing! t))
   (cons 'fill-things! (>fill-things! t))))

(define (<>universe t #:things [things #f])
  (unless (t 'has-procedure? 'fill-quality!)
    (t 'set-procedures! (>>make-fillable-procedures t)))
  (t 'set-procedures! (>>make-universe-procedures t))
  (when things (t 'fill-things! things))
  t)
