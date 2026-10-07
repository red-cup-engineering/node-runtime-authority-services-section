#lang racket

(provide <>client
         >>make-client-procedures
         >output-buffer
         >set-output-buffer!
         >append-output-buffer!
         >clear-output-buffer!
         >message!)

(define ((>output-buffer t))
  (log-debug "Querying ~a's output buffer" (t 'name))
  "")
(define ((>set-output-buffer! t) b)
  (log-debug "Setting ~a's output buffer to:\n  ~a"
             (t 'name) b)
  (t 'set-procedure! 'output-buffer (λ () b)))
(define ((>append-output-buffer! t) a)
  (log-debug "Appending ~a's output buffer with:\n  ~a"
             (t 'name) a)
  (t 'set-output-buffer!
     (string-join (list (t 'output-buffer) a) "")))
(define ((>clear-output-buffer! t))
  (log-debug "Clearing ~a's output buffer" (t 'name))
  (t 'set-output-buffer! ""))
(define ((>message! t) m)
  (log-debug "Registering message sent to ~a:\n  ~a"
             (t 'name) m)
  (t 'append-output-buffer! m))

(define (>>make-client-procedures t)
  (log-debug "Making client procedures for ~a" t)
  (list
   (cons 'output-buffer (>output-buffer t))
   (cons 'set-output-buffer! (>set-output-buffer! t))
   (cons 'append-output-buffer! (>append-output-buffer! t))
   (cons 'clear-output-buffer! (>clear-output-buffer! t))
   (cons 'message! (>message! t))))

(define (<>client t)
  (log-debug "Applying client quality to ~a" (t 'name))
  (t 'set-procedures! (>>make-client-procedures t))
  t)
