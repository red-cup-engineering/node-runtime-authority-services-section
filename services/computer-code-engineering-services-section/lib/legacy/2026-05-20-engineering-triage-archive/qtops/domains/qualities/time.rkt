#lang racket

(provide <>temporal
         >>make-time-procedures
         >stop-time
         >suspend-time
         >resume-time
         >time
         >clock
         >set-clock!
         >increment-clock!
         >tick!
         >schedule
         >set-schedule!
         >schedule-event!)

(define ((>stop-time t))
  (when (thread? (t 'time))
    (kill-thread (t 'time)))
  (t 'set-procedure! 'time (void)))
(define ((>suspend-time t))
  (when (thread? (t 'time))
    (thread-suspend (t 'time))))
(define ((>resume-time t))
  (when (thread? (t 'time))
    (thread-resume (t 'time))))

(define (>time t r)
  (define real-time
    (thread (λ () (let l () (t 'tick!) (sleep r) (l)))))
  (thread-suspend real-time)
  (λ () real-time))
(define ((>clock t))
  0)
(define ((>set-clock! t) n)
  (t 'set-procedure! 'clock (λ () n)))

(define ((>increment-clock! t) [n 1])
  (t 'set-clock! (+ (t 'clock) n)))

(define ((>tick! t))
  (t 'increment-clock!)
  (define events (first (t 'schedule)))
  (t 'set-schedule!
     (cond
       [(pair? (cdr (t 'schedule)))
        (cdr (t 'schedule))]
       [else (list (list))]))
  (let l ()
    (unless (null? events)
      (define event (car events))
      (set! events (cdr events))
      (event)
      (l))))

(define ((>schedule t))
  (list (list)))

(define ((>set-schedule! t) s)
  (t 'set-procedure! 'schedule (λ () s)))

(define ((>schedule-event! t) event [futureness 1])
  (define schedule (t 'schedule))
  ; we count moments different than Racket counts lists
  (define moment (- futureness 1))
  (when (< moment 0) (set! moment 0))
  (cond
    [(< moment (length schedule))
     (define schedule-moment
       (list-ref schedule moment))
     (t 'set-schedule!
        (list-set schedule
                  moment
                  (append schedule-moment
                          (list event))))]
    [else
     (define new-moments
       (build-list (- moment (length schedule)) values))
     (map (λ (_)
            (t 'set-schedule!
               (append (t 'schedule)
                       (list (list)))))
          new-moments)
     (t 'schedule-event! event moment)]))


(define (>>make-time-procedures t [r 0.2])
  (log-debug "Making time procedures for ~a."
             (if (t 'has-procedure? 'name) (t 'name) t))
  (list
   (cons 'stop-time (>stop-time t))
   (cons 'suspend-time (>suspend-time t))
   (cons 'resume-time (>resume-time t))
   (cons 'time (>time t r))
   (cons 'clock (>clock t))
   (cons 'set-clock! (>set-clock! t))
   (cons 'increment-clock! (>increment-clock! t))
   (cons 'tick! (>tick! t))
   (cons 'schedule (>schedule t))
   (cons 'set-schedule! (>set-schedule! t))
   (cons 'schedule-event! (>schedule-event! t))))

(define (<>temporal t)
  (t 'set-procedures! (>>make-time-procedures t))
  t)
