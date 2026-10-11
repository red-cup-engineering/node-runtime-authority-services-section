#lang racket

(require qtops/qualities/area
         qtops/qualities/lookable
         qtops/qualities/noise)

(provide <>eridrin)

(define (<>homes t)
  (<>noisy
    (<>lookable
      t #:name "cottages"
      #:description "There are 11 cottages around the road.")
    #:noises '("Sun glints off the smooth facade of a cottage."
               "There is a sound of conversation inside one cottage.")))

(define (<>riverbank t)
  (<>noisy
    (<>lookable
      t #:name "riverbank"
      #:description "The banks of the Marlbreen river are composed of small round pebbles. Most are an unremarkable beige, but there are a few bright blue pebbles.")
    #:noises '("A soft sound rises from the Marlbreen's banks as gravel shifts in place.")))

(define (<>grey-pebbles t)
  (<>lookable
    t #:name "beige pebbles"
    #:description "Most of the Marlbreen's banks and floors are covered in beige gravel."))

(define (<>silt t)
  (<>lookable
    t #:name "grey silt"
    #:description "Grey silt is suspended in the water of the Marlbreen River, obfuscating its bottom."))

(define (<>goat t)
  (<>noisy
    (<>lookable
      t #:name "goat"
      #:description "This is a goat.")
    #:noises '("The goat bleats."
               "The goat hacks up something yellow that nearly glows.")))

;; goat makes ambigris, more or less, from the blue pebbles.

(define (<>eridrin t)
  (<>area
   t #:name "Eridrin"
   #:description "This is the town of Eridrin. It consists of about a dozen wattle cottages erected near the gravel banks of the Marlbreen River, grey with silt. A well-worn road reveals sandy loam under thin topsoil. The road leads northwest to the large town of Bellybrush, and southeast through Marby County."))
