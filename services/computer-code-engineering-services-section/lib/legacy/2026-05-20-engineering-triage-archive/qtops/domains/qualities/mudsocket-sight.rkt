#lang racket

(provide make-sight-mudsocket-commands)

(define ((make-look-mudsocket-command t) a)
  (cond
    [(hash-empty? a)
     (cond
       [(and (t 'has-procedure? 'container)
             (procedure? (t 'container)))
        (define c (t 'container))
        (cond
          [(c 'has-procedure? 'looked-at-by-thing)
           (c 'looked-at-by-thing t)]
          [else
           (t 'look-thing! c)])]
       [else
        (t 'message! "You look around, but you aren't anyplace.")])]
    [(hash-has-key? a "container")
     (t 'message! "Looking inside things doesn't work yet.")]
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
        (t 'message! (format "You cannot see \"~a\"." l))]
       [(= (length m) 1)
        (define n (car m))
        (cond
          [(n 'has-procedure? 'looked-at-by-thing)
           (n 'looked-at-by-thing t)]
          [else
           (t 'look-thing! n)])]
       [else
        (t 'message!
           (format "There are multiple matches for \"~a\": ~a."
                   l (string-join (map
                      (λ (t)
                        (if (t 'has-procedure? 'name)
                            (t 'name)
                            t))
                      m) ", ")))])]))

(define (make-sight-mudsocket-commands t)
  (list
   (cons "look" (make-look-mudsocket-command t))))
