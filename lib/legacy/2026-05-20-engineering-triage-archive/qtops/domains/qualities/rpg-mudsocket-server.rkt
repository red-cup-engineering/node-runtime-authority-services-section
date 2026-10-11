#lang racket

(require qtops/qualities/notable
         qtops/qualities/mudsocket-client
         qtops/qualities/mudsocket-contents
         qtops/qualities/mudsocket-server
         qtops/qualities/mudsocket-sight
         qtops/qualities/mudsocket-speech
         qtops/qualities/mudsocket-trivia
         qtops/qualities/sight
         qtops/qualities/universe
         qtops/utilities/lists)

(provide <>rpg-mudsocket-server
         >>make-rpg-mudsocket-server-procedures)

(define ((>accept-mudsocket-connection t) c)
  (<>sighted (<>notable c))
  (map
   (λ (p) (c 'set-mudsocket-commands! (p c)))
   (list make-container-mudsocket-commands
         make-sight-mudsocket-commands
         make-speech-mudsocket-commands
         make-trivia-mudsocket-commands))
  (when (and (c 'has-procedure? 'universe)
             ((c 'universe) 'has-procedure? 'spawn-room))
    (c 'move-thing!! ((c 'universe) 'spawn-room))))

(define (>>make-rpg-mudsocket-server-procedures t)
  (list
   (cons 'accept-mudsocket-connection
         (>accept-mudsocket-connection t))))

(define (<>rpg-mudsocket-server t)
  (unless (t 'has-procedure? 'mudsocket-tick!)
    (<>mudsocket-server t))
  (t 'set-procedures! (>>make-rpg-mudsocket-server-procedures t))
  t)
