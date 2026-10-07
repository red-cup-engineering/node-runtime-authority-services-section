#lang racket

(provide make-harvest-mudsocket-commands)

(define ((make-harvest-mudsocket-command t) a)
  (cond
    [(hash-empty? a)
     (cond
       [(and (t 'has-procedure? 'container)
             (procedure? (t 'container)))
        (define c (t 'container))
        (cond
          [(c 'has-procedure? 'harvestable?)
           (if (c 'harvestable?)
               (c 'harvest! t)
               (t 'message! "You can't harvest that right now."))]
          [else
           (t 'message! "You can't harvest from here - maybe try harvesting a specific thing.")])]
       [else
        (t 'message! "You can't harvest from here, because you are no place.")])]
    [(hash-has-key? a 'line)
     (define l (hash-ref a 'line))
     (log-debug "Trying to look at ~a" l)
     (define m ((t 'container) 'search-contents-by-term l))
     (when ((t 'container) 'term=? l)
       (set! m (append m (list (t 'container)))))
     (map
      (λ (e)
        (define f (symbol->string e))
        (when (string=? f l)
          (set! m (append m (list ((t 'container) 'exit e))))))
      (hash-keys ((t 'container) 'exits)))
     (log-debug "Matches are ~a" m)
     (cond
       [(null? m)
        (t 'message! (format "You cannot harvest \"~a\"." l))]
       [(= (length m) 1)
        (define n (car m))
        (cond
          [(n 'has-procedure? 'harvestable?)
           (if (n 'harvestable?)
               (n 'harvest! t)
               (t 'message! "You cannot harvest that right now."))]
          [else
           (t 'message! "You cannot harvest that.")])]
       [else
        (t 'message!
           (format "There are multiple matches for \"~a\": ~a."
                   l (string-join (map
                      (λ (t)
                        (if (t 'has-procedure? 'name)
                            (t 'name)
                            t))
                      m) ", ")))])]))

(define (make-harvest-mudsocket-commands t)
  (list
   (cons "harvest" (make-harvest-mudsocket-command t))))
