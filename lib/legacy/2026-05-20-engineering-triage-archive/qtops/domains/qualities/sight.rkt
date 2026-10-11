#lang racket

(provide <>sighted
         >>make-sight-procedures
         >look-thing!)

(define ((>look-thing! t) o)
  (define r "")
  (define R (λ (b) (set! r (string-join (list r b) ""))))
  (define c
    (cond
      [(o 'has-procedure? 'contents)
       (filter procedure?
               (map (λ (t) (when (and (t 'has-procedure? 'name)
                                      (t 'has-procedure? 'notable?)
                                      (t 'notable?))
                             t))
                    (o 'contents)))]
      [else #f]))
  (when (o 'has-procedure? 'name)
    (R (format "[  ~a  ]\n" (o 'name))))
  (when (o 'has-procedure? 'description)
    (R (format "~a\n" (o 'description))))
  (when (and (o 'has-procedure? 'exits)
             (not (null? (hash-keys (o 'exits)))))
    (R (format "  Exits: ~a\n"
               (string-join (map
                             (λ (s) (symbol->string s))
                             (hash-keys (o 'exits))) ", "))))
  (when c
    (R (format "Contents: ~a\n"
               (string-join (map (λ (w)
                                   (if (eq? w t)
                                       "you"
                                       (w 'name)))
                                 c)
                            ", "))))
  (cond
    [(> (string-length r) 0) (t 'message! r)]
    [else (t 'message! "You can't look at that.")]))

(define (>>make-sight-procedures t)
  (list
   (cons 'look-thing! (>look-thing! t))))

(define (<>sighted t)
  (t 'set-procedures! (>>make-sight-procedures t))
  t)
