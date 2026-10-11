#lang racket

(require "animation.rkt"
         "../utilities/lists.rkt")

(provide <>noisy
         >>make-noise-procedures
         >noises
         >set-noises!
         >add-noises!
         >add-noise!
         >noise
         >make-noise^!)

(define ((>noises t)) (list))
(define ((>set-noises! t) N)
  (t 'set-procedure! 'noises (λ () N)))
(define ((>add-noises! t) N)
  (t 'set-noises! (append (t 'noises) N)))
(define ((>add-noise! t) n)
  (t 'add-noises! (list n)))
(define ((>noise t))
  (random-element (t 'noises)))
(define ((>make-noise^! t))
  (define noise (if (procedure? (t 'noise)) ((t 'noise)) (t 'noise)))
  ((t 'with-procedure~~ 'message-contents^!) noise)
  ((t 'with-procedure~~ 'message-container-contents^!) noise))

(define (>>make-noise-procedures t)
  (list
   (cons 'noises (>noises t))
   (cons 'set-noises! (>set-noises! t))
   (cons 'add-noises! (>add-noises! t))
   (cons 'add-noise! (>add-noise! t))
   (cons 'noise (>noise t))
   (cons 'make-noise^! (>make-noise^! t))))

(define (<>noisy t
                 #:noises [n #f]
                 #:frequency [f (random 120 300)]
                 #:chance [c 100])
  (unless (t 'has-procedure? 'animations)
    (t 'set-procedures! (>>make-animation-procedures t)))
  (unless (t 'has-procedure? 'noises)
    (t 'set-procedures! (>>make-noise-procedures t)))
    (when n (t 'add-noises! n))
  ((t 'with-procedure~~ 'add-animation!) (list 'make-noise^! f c))
  t)
