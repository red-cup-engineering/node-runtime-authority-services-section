#lang racket

(require qtops/qualities/pronouns
         qtops/qualities/region
         qtops/qualities/region-noise
         "airlock.rkt"
         "bridge.rkt"
         "engine-room.rkt"
         "passageways.rkt"
         "quarters.rkt")

(provide <>okaga)

(define (<>okaga t)
  (<>noisy-region
   (<>region
    t #:name "Okaga"
    #:description "This is the Okaga, emsenn's personal starship."
    #:areas `((airlock ,<>airlock)
                         (bridge ,<>bridge)
                         (engine-room ,<>engine-room)
                         (fore-passageway ,<>fore-passageway)
                         (aft-passageway ,<>aft-passageway)
                         (quarters ,<>quarters))
    #:links '((airlock "port" "starboard" bridge)
              (bridge "port" "starboard" quarters)
              (bridge "aft" "fore" fore-passageway)
              (fore-passageway "aft" "fore" aft-passageway)
              (aft-passageway "aft" "fore" engine-room)))
   #:noises (list (t 'prerender-string
                     '("Deep pops and creeks shudder the "
                       name " as " pronoun-s3 " adjusts to "
                       "fluctuations in the universe outside "
                       pronoun-dp3 " hull.")))
   #:frequency (λ () (random 2000 4800)))
  (t 'set-procedures! (>>make-she-pronoun-procedures t))
  t)
