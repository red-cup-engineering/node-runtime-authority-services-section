#lang racket

(require qtops/qualities/area
         qtops/qualities/lookable
         qtops/qualities/noise)

(provide <>quarters)

(define (<>ship t)
  (<>lookable
   t #:name "ship"
   #:description "This is a compartment within a ship. Without ports or a sense of motion, it's difficult to tell exactly what sort of ship."))
(define (<>hull t)
  (<>lookable
   t #:name "hull"
   #:description "The interior of the ship's hull is, here, coated in some sort of white paint with an eggshell texture."
   #:adjectives '("interior" "coated" "painted" "white")))
(define (<>deckhead t)
  (<>lookable
   t #:name "deckhead"
   #:description "The deckhead is a tight grid of gray squares. A few, seemingly at random, are lighting the area."
   #:nouns '("ceiling" "lights")))
(define (<>port-bulkhead t)
  (<>lookable
   t #:name "port bulkhead"
   #:description "The bulkhead to port is painted with a glossy blue paint."
   #:nouns '("bulkhead")
   #:adjectives '("port" "painted" "glossy" "blue")))
(define (<>aft-bulkhead t)
  (<>lookable
   t #:name "aft bulkhead"
   #:description "The porthead to aft is painted with the same white paint as the hull."
   #:nouns '("bulkhead")
   #:adjectives '("aft" "painted" "white")))
(define (<>fore-bulkhead t)
  (<>lookable
   t #:name "fore bulkhead"
   #:description "The bulkhead to fore is painted with the same white paint as the hull."
   #:nouns '("bulkhead")
   #:adjectives '("fore" "painted" "white")))

(define (<>quarters t)
  (<>noisy
    (<>area
      t #:name "quarters"
      #:description "This compartment is obviously used for quarters. A small kitchen has been set up against the hull to port, opposite the door to the bridge. Against the aft bulkhead is a pallet."
      #:contents (list <>ship <>hull <>deckhead <>port-bulkhead
                       <>aft-bulkhead <>fore-bulkhead))
    #:noises
    '("A compressor under the deck buzzes."
      "A low mechanical hum swells and fades in the passageway.")
    #:frequency (λ () (random 2000 4800))))
