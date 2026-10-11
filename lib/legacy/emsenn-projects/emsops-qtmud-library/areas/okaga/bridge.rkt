#lang racket

(require qtops/qualities/area
         qtops/qualities/lookable
         qtops/qualities/noise)

(provide <>bridge)


#; (define (»ikmu t)
  (define (move-to-random-exit)
    (define E (hash-values ((t 'container) 'exits)))
    (when (not (null? E))
      (t 'move-thing! (random-element E))))
  (define (mew)
    (define (n) (t 'name)) (define (dp3) (t 'pronoun-dp3))
    (define (s3) (t 'pronoun-s3))
    (t 'message-container-contents!
       (random-element
        (list
         ((§ (n) " raises " (dp3) " face and squints " (dp3)
             " eyes; " (dp3) " wrinkles rapidly as " (s3)
             " explores some scent " (s3) " caught."))
         ((§ (n) " looks around the room from " (dp3)
             " current position, before moving to a new spot "
             "and stretching out on " (dp3) " side."))
         ((§ (n) " suddenly leans back and grooms " (dp3)
             " shoulders with " (dp3) " tongue for a moment."))))))
  (t 'set-procedures!
     (make-animate-procedures
      t (list mew mew mew move-to-random-exit)
      (random 120 200)))
  ((t 'universe) 'schedule-event! (t 'procedure 'animate))
  (»lookable
    t #:name "Ikmu"
    #:description (§ "This is " (λ () (t 'name))
                     ", a calico cat.")
    #:nouns '("cat" "feline")
    #:adjectives '("calico" "little" "painted"))
  (»npc
    t #:pronouns make-she-pronoun-procedures))

(define (<>ship t)
  (<>lookable
   t #:name "ship"
   #:description "The fixtures of the room make it clear this is a ship. What sort is revealed only by the view out the front window: a cavalcade of stars."))
(define (<>consoles t)
  (<>lookable
   t #:name "consoles"
   #:description "The consoles in the center of the room are held up by thick posts made of dull gray metal. On their surface, textured with verdigris, there are a variety of instruments for, presumably, monitoring and controlling the craft."
  #:adjectives '("petinaed")))
(define (<>instruments t)
  (<>lookable
   t #:name "instruments"
   #:description "The face of the console is covered in analog dials of various sizes, and a variety of brass levers and wheels rise up. Most are shiny from use, though hold a deep petina over the untouched parts."
   #:nouns '("dials" "wheels" "levers" "face")
   #:adjectives '("brass" "analog" "petinaed")))
(define (<>center t)
  (<>lookable
   t #:name "center"
   #:description "The center of the room, presumably where the ship's captain would stand, is directly under the sole light in the room, an off-white hemisphere embedded in the deckhead. Most of the instruments would be acccessible from here."))
(define (<>fore t)
  (<>lookable
   t #:name "fore hull"
   #:description "To the fore is the hull of the ship, which has a large window embedded in it."
   #:nouns '("fore" "hull" "bow")
   #:adjectives '("fore")))
;; ^-- this seems silly, #:nouns '("fore" ("hull" ("fore")))?
;; otherwise folk can "look fore fore"
(define (<>window t)
  (<>lookable
   t #:name "window"
   #:description "The window to fore, which covers almost the whole width of that section of the hull, provides a view of space: a vast rainbow static."))
(define (<>glass t)
  (<>lookable
   t #:name "glass"
   #:description "The glass that fills the window is very thick, and appears to distort the view around the edges rather severely."))
(define (<>stars t)
  (<>lookable
   t #:name "stars"
   #:description  "The stars outside the window are too abundant to make much sense of: while at a glance a few stars seem to be distinctive, the background quickly coalesces into a field of stars, as dense as static: there is no place uninfluenced by the twinkle."))



(define (<>fixtures t)
  (<>lookable
   t #:name "fixtures"
   #:description "The fixtures of this room make its purpose clear: it is the place for operating a ship."))



(define (<>bridge t)
  (<>noisy
   (<>area
    t #:name "bridge"
    #:description "This is the bridge of a ship. Two consoles of analog dials, peppered with brass wheels and levers, flank the center of the room, angled slightly to form an open arrow pointing to the ship's bow, where there is a window paneled with thick glass. From here, open doors lead starboard, to the airlock, and port, to the quarters. A door aft leads to a passageway."
    #:contents (list <>ship <>consoles <>instruments <>center <>fore
                     <>window <>glass <>stars <>fixtures #;<>ikmu))
   #:noises
   '("A few dials on the consoles slowly twist and settle into new positions.")
   #:frequency (λ () (random 1800 2000))))
