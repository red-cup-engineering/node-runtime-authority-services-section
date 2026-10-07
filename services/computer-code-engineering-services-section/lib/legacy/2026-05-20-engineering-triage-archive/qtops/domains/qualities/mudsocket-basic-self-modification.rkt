#lang racket

(provide make-self-modification-mudsocket-command)

(define (make-self-modification-mudsocket-command t)
  (unless (procedure? t)
    (raise-argument-error 'make-self-modification-mudsocket-command
                          "procedure?"
                          t))
  (λ (a)
    (if (hash-has-key? a 'procedure)
        (if (hash-has-key? a 'line)
            (with-handlers ([exn:fail?
                             (λ (e)
                               ((t 'with-procedure 'message!)
                                (format
                                 "Failed to call: ~a" e)))])
              (t (string->symbol
                  (hash-ref a 'procedure))
                 (hash-ref a 'line)))
            (t (string->symbol
                (hash-ref a 'procedure))))
        ((t 'with-procedure 'message!)
         "You must specify a procedure."))))
