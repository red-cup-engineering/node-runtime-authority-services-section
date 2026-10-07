#lang racket

(provide make-container-mudsocket-commands)

(define ((make-move-mudsocket-command t) a)
  (cond
    [(and (t 'has-procedure? 'container)
          (procedure? (t 'container)))
     (cond
       [(hash-has-key? a 'line)
        (define l (string->symbol (hash-ref a 'line)))
        (cond
          [(hash-has-key? ((t 'container) 'exits) l)
           (define d (hash-ref ((t 'container) 'exits) l))
           (t 'move-thing!! d)
           (t 'message!
              (format "You move; your location is now ~a.~a"
                      (d 'name)
                      (cond
                        [(d 'has-procedure? 'exits)
                         (format "\n  Exits: ~a"
                                 (string-join
                                  (map (λ (e) (symbol->string e))
                                       (hash-keys (d 'exits)))
                                  ", "))]
                        [else ""])))]
          [else
           (t 'message!
              (format "You fail to move; ~a is an invalid exit."
                      l))])]
       [else
        (t 'message! "You must use this command with an exit; try and \"look\" for one.")])]
    [else
     (t 'message! "You can't move, because you aren't anyplace.")]))

(define (make-container-mudsocket-commands t)
  (list
   (cons "move" (make-move-mudsocket-command t))))
