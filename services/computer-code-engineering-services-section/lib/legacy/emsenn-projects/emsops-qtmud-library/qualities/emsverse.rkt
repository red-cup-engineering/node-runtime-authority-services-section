#lang racket

(require qtops/utilities/lists
         qtops/qualities/notable
         qtops/qualities/mudsocket-contents
         qtops/qualities/mudsocket-sight
         qtops/qualities/mudsocket-speech
         qtops/qualities/mudsocket-trivia
         qtops/qualities/sight
         "mudsocket-client.rkt")

(provide <>emsverse
         >>make-emsverse-procedures
         >accept-mudsocket-connection
         >make-emsmud-splash)

(define ((>accept-mudsocket-connection u) c)
  (<>sighted (<>notable (<>mudsocket-client c)))
  (map
   (λ (p) (c 'set-mudsocket-commands! (p c)))
   (list
    make-container-mudsocket-commands
    make-sight-mudsocket-commands
    make-speech-mudsocket-commands
    make-trivia-mudsocket-commands))
  (when (and (c 'has-procedure? 'universe)
             ((c 'universe) 'has-procedure? 'spawn-room))
    (c 'move-thing!! ((c 'universe) 'spawn-room))))

(define ((>make-emsmud-splash u))
  (random-element
   (list
    "in midst of a million nightmares, a chance for one dream"
    "a symphony for a feud"
    "don't forget temptation"
    "let nothing human disgust you")))

(define (>>make-emsverse-procedures u)
  (list
   (cons 'accept-mudsocket-connection
         (>accept-mudsocket-connection u))
   (cons 'make-emsmud-splash
         (>make-emsmud-splash u))))

(define (<>emsverse t)
  (t 'set-procedures! (>>make-emsverse-procedures t))
  t)
