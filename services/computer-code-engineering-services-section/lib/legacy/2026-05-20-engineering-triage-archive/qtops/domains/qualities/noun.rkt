#lang racket

(provide <>noun
         >>make-noun-procedures
         >nouns
         >set-nouns!
         >add-nouns!
         >add-noun!
         >noun=?
         >adjectives
         >set-adjectives!
         >add-adjectives!
         >add-adjective!
         >adjective=?)

(define ((>nouns t)) (list))
(define ((>set-nouns! t) N)
  (t 'set-procedure! 'nouns (λ () N)))
(define ((>add-nouns! t) N)
  (t 'set-nouns! (append (t 'nouns) N)))
(define ((>add-noun! t) n)
  (t 'add-nouns! (list n)))
(define (>noun=? t)
  (define (real-noun=? l)
    (define w (last (string-split l)))
    (or (ormap (λ (n)
                 (or (string=? n w)
                     (string=? (string-downcase n) w)))
               (t 'nouns))))
  (cond
    [(t 'has-procedure? 'term=?)
     (define old-term=? (t 'procedure 'term=?))
     (t 'set-procedure! 'term=?
        (λ (l) (or (old-term=? l) (real-noun=? l))))]
    [else
     (t 'set-procedure! 'term=? real-noun=?)])
  real-noun=?)

(define ((>adjectives t)) (list))
(define ((>set-adjectives! t) A)
  (t 'set-procedure! 'adjectives (λ () A)))
(define ((>add-adjectives! t) A)
  (t 'set-adjectives! (append (t 'adjectives) A)))
(define ((>add-adjective! t) a)
  (t 'add-adjectives! (list a)))
(define (>adjective=? t)
  (define (real-adjective=? l)
    (define A (reverse (cdr (reverse (string-split l)))))
    (or (ormap (λ (n)
                 (if (or (member n A)
                       (member (string-downcase n) A))
                  #t #f))
               (t 'adjectives))))
  (cond
    [(t 'has-procedure? 'term=?)
     (define old-term=? (t 'procedure 'term=?))
     (t 'set-procedure! 'term=?
        (λ (l)
          (if (> (length (string-split l)) 1)
              (and (old-term=? l) (real-adjective=? l))
              (old-term=? l))))]
    [else
     (t 'set-procedure! 'term=? real-adjective=?)])
  real-adjective=?)



(define (>>make-noun-procedures t)
  (list
   (cons 'nouns (>nouns t))
   (cons 'set-nouns! (>set-nouns! t))
   (cons 'add-nouns! (>add-nouns! t))
   (cons 'add-noun! (>add-noun! t))
   (cons 'noun=? (>noun=? t))
   (cons 'adjectives (>adjectives t))
   (cons 'set-adjectives! (>set-adjectives! t))
   (cons 'add-adjectives! (>add-adjectives! t))
   (cons 'add-adjective! (>add-adjective! t))
   (cons 'adjective=? (>adjective=? t))))

(define (<>noun t
                #:nouns [nouns #f]
                #:adjectives [adjectives #f])
  (unless (t 'has-procedure? 'nouns)
    (t 'set-procedures! (>>make-noun-procedures t)))
  (when nouns (t 'set-nouns! nouns))
  (when adjectives (t 'set-adjectives! adjectives))
  t)
