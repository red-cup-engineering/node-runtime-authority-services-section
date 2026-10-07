#lang racket

(require qtops/qualities/fillable)

(provide <>library
         >>make-library-procedures)

(define (>documents t)
  (define real-documents (make-hash))
  (λ () real-documents))
(define ((>has-document? t) k) (hash-has-key? (t 'documents) k))
(define ((>document t) k) (hash-ref (t 'documents) k))
(define ((>set-document! t) k d)
  (hash-set! (t 'documents) k d))
(define ((>set-documents! t) D)
  (map
   (λ (d) (t 'set-document! (car d) (cdr d)))
   D))
(define ((>remove-document! t) k)
  (hash-remove! (t 'documents) k))
(define ((>fill-documents! t) D)
  (hash-map
   (make-hash D)
   (λ (k d)
     (define w
       (first
        (t 'fill-quality!
           'areas d)))
     (t 'set-document! k w))))

(define (>>make-library-procedures t)
  (define LP
    ((λ ()
       (define lp '())
       (λ ([l #f]) (if l (set! lp (append lp l)) lp)))))
  (unless (t 'has-procedure? 'fill-quality!)
    (LP (>>make-fillable-procedures t)))
  (LP
   (list
    (cons 'documents (>documents t))
    (cons 'has-document? (>has-document? t))
    (cons 'document (>document t))
    (cons 'set-document! (>set-document! t))
    (cons 'set-documents! (>set-documents! t))
    (cons 'fill-documents! (>fill-documents! t))))
  (LP))

(define (<>library t
                    #:name [name #f]
                    #:documents [documents #f])
  (when name (t 'set-name! name))
  (unless (t 'has-procedure? 'documents)
    (t 'set-procedures! (>>make-library-procedures t)))
  (when documents (t 'fill-documents! documents))
  t)
