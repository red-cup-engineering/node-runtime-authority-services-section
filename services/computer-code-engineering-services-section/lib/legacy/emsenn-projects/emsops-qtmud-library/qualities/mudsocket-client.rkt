#lang racket

(provide <>mudsocket-client
         >>make-mudsocket-client-procedures
         >make-mudsocket-connection-message)

(define ((>make-mudsocket-connection-message t))
  (define R
    ((λ () (define r "")
        (λ ([m #f]) (if m (set! r (string-append r m)) r)))))
  (R (format "Your connection~a has been accepted."
             (cond
               [(and (t 'has-procedure? 'universe)
                     ((t 'universe) 'has-procedure? 'name))
                (format " to ~a"
                        ((t 'universe) 'name))]
               [else ""])))
  (when (and (t 'has-procedure? 'universe)
             ((t 'universe) 'has-procedure? 'make-emsmud-splash))
    (R (format "\n  ...~a\n\n"
               ((t 'universe) 'make-emsmud-splash))))
  (R "\nThis is a dimension, within yours but with different rules. Type instructions then press ENTER. Try starting with \"help\"")
  (R))

(define (>>make-mudsocket-client-procedures t)
  (list
   (cons 'make-mudsocket-connection-message
         (>make-mudsocket-connection-message t))))

(define (<>mudsocket-client t)
  (t 'set-procedures! (>>make-mudsocket-client-procedures t))
  t)
