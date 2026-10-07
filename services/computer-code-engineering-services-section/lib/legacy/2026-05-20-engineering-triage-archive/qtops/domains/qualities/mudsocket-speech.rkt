#lang racket

(provide make-speech-mudsocket-commands)

(define ((make-say-mudsocket-command t) a)
  (if (and (t 'has-procedure? 'container)
           (procedure? (t 'container)))
      (if (hash-has-key? a 'line)
          (t 'message-container-contents^!
             (format "~a says: ~a"
                     (if (t 'has-procedure? 'name)
                         (t 'name)
                         "Something")
                     (hash-ref a 'line)))
          (t 'message! "You have to say something."))
      (t 'message! "You have to be someplace to say something.")))

(define (make-speech-mudsocket-commands t)
  (list
   (cons "say" (make-say-mudsocket-command t))))
