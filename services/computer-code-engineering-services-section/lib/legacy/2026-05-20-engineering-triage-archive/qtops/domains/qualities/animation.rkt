#lang racket


(provide <>animate
         >>make-animation-procedures)

(define (animations-list? A)
  (and (list? A)
                 (andmap list? A)
                 (andmap (λ (a)
                           (and (or (symbol? (first a))
                                    (procedure? (first a)))
                                (or (integer? (second a))
                                    (procedure? (second a)))
                                (or (integer? (third a))
                                    (procedure? (third a)))))
                         A)))

(define (>animations t)
  (unless (procedure? t)
    (raise-argument-error '>animations
                          "procedure?"
                          t))
  (log-debug "Creating animations procedure for ~a" (t 'name))
  (λ ()
    (log-debug "Querying ~a's animations" (t 'name))
    (list)))

(define (>set-animations! t)
  (unless (procedure? t)
    (raise-argument-error '>set-animations!
                          "procedure?"
                          t))
  (log-debug "Creating set-animations! procedure for ~a" (t 'name))
  (λ (A)
    (unless (animations-list? A)
      (raise-argument-error
       'set-animations!
       "listof (list procedure (proc/int) (proc/int)"
       A))
    (log-debug "Setting ~a's animations to ~a" (t 'name) A)
    (t 'set-procedure!
       'animations
       (λ ()
         (log-debug "Querying ~a's animations." (t 'name))
         A))))


(define (>add-animations! t)
  (unless (procedure? t)
    (raise-argument-error '>add-animations!
                          "procedure?"
                          t))
  (log-debug "Creating add-animations! procedure for ~a" (t 'name))
  (λ (A)
    (unless (animations-list? A)
      (raise-argument-error
       'add-animations!
       "listof (list proc (proc/int) (proc/int))"
       A))
    (log-debug "Adding to ~a's animations: ~a" (t 'name) A)
    (t 'set-animations! (append (t 'animations) A))))
(define (>add-animation! t)
  (unless (procedure? t)
    (raise-argument-error '>add-animation!
                          "procedure?"
                          t))
  (log-debug "Creating add-animation! procedure for ~a" (t 'name))
  (λ (a)
    (log-debug "Adding ~a to ~a's animations" a (t 'name))
    (t 'add-animations! (list a))))

(define ((>remove-animation! t) k)
  (t 'set-animations!
     (filter list?
             (map
              (λ (n)
                (when (not (eq? (car n) k)) k))
              (t 'animations)))))

(define (>animate~~ t)
  (unless (procedure? t)
    (raise-argument-error '>animate~~
                          "procedure?"
                          t))
  (log-debug "Creating animate~~ procedure for ~a" (t 'name))
  (λ ()
    (log-debug "Processing ~a's animations" (t 'name))
    (define i 120)
    (define it? #f)
    (map
     (λ (a)
       (log-debug "Processing ~a's ~a animation"
                  (t 'name) a)
       (define p (t 'procedure (car a)))
       (define f (let ([w (car (cdr a))]) (if (procedure? w) (w) w)))
       (define c (let ([w (car (cdr (cdr a)))])
                   (if (procedure? w) (w) w)))
       (when (and (> f i) (eq? it? #f))
         (set! i f) (set! it? #t))
       (when (< f i)
         (set! i f) (set! it? #t))
       (when (<= c 100)
         (if (t 'has-procedure? 'schedule-event!)
             (t 'schedule-event! p f)
             (if (t 'has-procedure? 'universe)
                 ((t 'universe) 'schedule-event! p f)
                 (log-warning
                  "~a has no universe: cannot schedule animation ~a"
                  (t 'name) a)))))
     (t 'animations))
    (if (t 'has-procedure? 'schedule-event!)
        (t 'schedule-event! (t 'procedure 'animate~~) i)
        (if (t 'has-procedure? 'universe)
            ((t 'universe) 'schedule-event!
                           (t 'procedure 'animate~~) i)
            (log-warning
             "~a lacks universe: cannot rechedule animation.")))))


(define (>>make-animation-procedures t)
  (list
   (cons 'animations (>animations t))
   (cons 'set-animations! (>set-animations! t))
   (cons 'add-animations! (>add-animations! t))
   (cons 'add-animation! (>add-animation! t))
   (cons 'remove-animation! (>remove-animation! t))
   (cons 'animate~~ (>animate~~ t))))

(define (<>animate t)
  (t 'set-procedures! (>>make-animation-procedures t))
  t)
