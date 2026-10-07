#lang racket

(require "noise.rkt")

(provide <>noisy-region)

(define (<>noisy-region t
                        #:noises [noises #f]
                        #:frequency [frequency
                                     (λ () (random 120 300))]
                        #:chance [chance 100])
  (unless (t 'has-procedure? 'noises)
    (<>noisy
     t #:noises noises #:frequency frequency #:chance chance))
  (t 'set-procedure! 'make-noise^!
     (λ ()
       (define n (if (string? (t 'noise)) (t 'noise) ((t 'noise))))
       (map (λ (a) (a 'message-contents^! n))
            (hash-values (t 'areas))))))
