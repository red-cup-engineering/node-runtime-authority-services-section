#lang racket

(provide <>mudsocket-client
         >>make-mudsocket-client-procedures
         >mudsocket-output-buffer
         >set-mudsocket-output-buffer!
         >append-mudsocket-output-buffer!
         >clear-mudsocket-output-buffer!
         >send-mudsocket-output-buffer!
         >mudsocket-commands
         >set-mudsocket-commands!
         >set-mudsocket-command!
         >parse-mudsocket-line
         make-commands-mudsocket-command
         make-help-mudsocket-command
         make-whoami-mudsocket-command
         make-default-mudsocket-commands)

(define ((>mudsocket-output-buffer t)) "")
(define (>set-mudsocket-output-buffer! t)
  (t 'set-procedure! 'set-output-buffer!
     (λ (b)
       (t 'set-mudsocket-output-buffer! b)))
  (λ (b)
    (t 'set-procedure! 'mudsocket-output-buffer (λ () b))))
(define (>append-mudsocket-output-buffer! t)
  (t 'set-procedure! 'append-output-buffer!
     (λ (b) (t 'append-mudsocket-output-buffer! b)))
  (λ (b) (t 'set-mudsocket-output-buffer!
            (string-join (list (t 'mudsocket-output-buffer) b) ""))))
(define (>clear-mudsocket-output-buffer! t)
  (t 'set-procedure! 'clear-output-buffer!
     (λ () (t 'clear-mudsocket-output-buffer!)))
  (λ () (t 'set-mudsocket-output-buffer! "")))

(define ((>send-mudsocket-output-buffer! t))
  (define mob (t 'mudsocket-output-buffer))
  (with-handlers
    ([exn? (λ (e) (log-warning "~a" e))])
    (display
     (format
      (cond
        [(eq? #\newline (last (string->list mob))) "~a"]
        [else "~a\n"])
      mob)
     (t 'mudsocket-out))
    (flush-output (t 'mudsocket-out)))
  (t 'clear-mudsocket-output-buffer!))

(define (>mudsocket-commands t)
  (define real-commands (make-hash))
  (λ () real-commands))
(define ((>set-mudsocket-commands! t) C)
  (map
   (λ (c)
     (hash-set! (t 'mudsocket-commands) (car c) (cdr c)))
   C))
(define ((>set-mudsocket-command! t) k p)
  (t 'set-mudsocket-commands! (list (cons k p))))

(define (>parse-mudsocket-line t)
  (define (parse-args args)
    (define results (make-hash))
    (map
     (λ (a)
       (cond
         [(and (> (string-length a) 2)
               (string=? (substring a 0 2) "--"))
          (define sa (string-split a "="))
          (define ak (substring (car sa) 2))
          (define av (cdr sa))
          (hash-set! results ak av)]
         [(string=? (substring a 0 1) "-")
          (map
           (λ (c)
             (hash-set! results c #t))
           (string->list (substring a 1)))]
         [else
          (hash-set!
           results 'line
           (cond
             [(hash-has-key? results 'line)
              (append (hash-ref results 'line) (list a))]
             [else
              (list a)]))]))
     args)
    (when (hash-has-key? results 'line)
      (hash-set!
       results 'line
       (string-join (hash-ref results 'line))))
    results)
  (λ (l)
    (define reply "")
    (define cmds (t 'mudsocket-commands))
    (when (> (string-length l) 0)
      (define sl (string-split l))
      (define fw (car sl))
      (define args (parse-args (cdr sl)))
      (cond
        [(hash-has-key? cmds fw)
         ((hash-ref cmds fw) args)]
        [else (set! reply "Invalid command.")]))
    (when (> (string-length reply) 0)
      (t 'message! reply))))

(define ((make-commands-mudsocket-command t) a)
  (cond
    [(hash-has-key? a #\H)
     (t 'message "syntax: commands [-H]\nShows a list of accessible commands. If H is passed, shows this help text instead.")]
    [else
     (t 'message!
        (format "You have acquired the following commands:: ~a"
                (string-join (hash-keys (t 'mudsocket-commands)) ", ")))]))

(define ((make-help-mudsocket-command t) a)
  (t 'message!
     (format "You are currently connected to ~a. To interact, input instructions and press ENTER. To view a list of available commands, try \"commands\"."
             (cond
               [(and (t 'has-procedure? 'universe)
                     ((t 'universe) 'has-procedure? 'name))
                ((t 'universe) 'name)]
               [else "an artificial dimension"]))))

(define ((make-whoami-mudsocket-command t) a)
  (t 'message! (t 'name)))

(define (make-default-mudsocket-commands t)
  (list
   (cons "commands" (make-commands-mudsocket-command t))
   (cons "help" (make-help-mudsocket-command t))
   (cons "whoami" (make-whoami-mudsocket-command t))))


(define (>>make-mudsocket-client-procedures t in out ip port)
  (log-debug "Making MUDSocket client procedures for ~a"
             (if (t 'has-procedure? 'name) (t 'name) t))
  (list
   (cons 'mudsocket-in (λ () in))
   (cons 'mudsocket-out (λ () out))
   (cons 'mudsocket-ip (λ () ip))
   (cons 'mudsocket-port (λ () port))
   (cons 'mudsocket-output-buffer (>mudsocket-output-buffer t))
   (cons 'set-mudsocket-output-buffer!
         (>set-mudsocket-output-buffer! t))
   (cons 'append-mudsocket-output-buffer!
         (>append-mudsocket-output-buffer! t))
   (cons 'clear-mudsocket-output-buffer!
         (>clear-mudsocket-output-buffer! t))
   (cons 'send-mudsocket-output-buffer!
         (>send-mudsocket-output-buffer! t))
   (cons 'parse-mudsocket-line
         (>parse-mudsocket-line t))
   (cons 'mudsocket-commands
         (>mudsocket-commands t))
   (cons 'set-mudsocket-commands!
         (>set-mudsocket-commands! t))
   (cons 'set-mudsocket-command!
         (>set-mudsocket-command! t))))

(define (<>mudsocket-client t
                            #:in in
                            #:out out
                            #:ip ip
                            #:port port
                            #:mudsocket-commands
                            [mudsocket-commands #f])
  (t 'set-procedures!
     (>>make-mudsocket-client-procedures t in out ip port))
  (when mudsocket-commands
    (t 'set-mudsocket-commands! mudsocket-commands))
  t)
