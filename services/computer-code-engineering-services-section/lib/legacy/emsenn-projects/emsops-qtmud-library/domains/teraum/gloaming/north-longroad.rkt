#lang racket

(require qtops/qualities/area
         qtops/qualities/lookable
         "../../../qualities/gloamer.rkt")

(define (<>gray-gravel t)
  (<>lookable
   t #:name "gray gravel"
   #:nouns '("gravel")
   #:adjectives '("gray")
   #:description "The gray gravel that paves the Longroad is clearly not from here."))

(define (<>road t)
  (<>lookable
   t #:name "Longroad"
   #:nouns '("road")
   #:description "The Longroad ends not too far to the north, as it intersects with the Kingsroad, but it extends hundreds of miles south and southeast from here. Eventually, after passing through the Gloaming, into the Unseen Sea, it ends at the gates of the human city of Tayopopolis.

The road itself is gray gravel, notable for being different in colour than the indigenous stone, which has a more red hue."))

(define (<>north-longroad t)
  (<>Gloamer
   (<>area
    t #:name "Longroad"
    #:description "This is a stretch of the Longroad, as it meanders into the marshy Gloaming. The road ends not too far to the north, as it intersects with the Kingsroad, but it extends hundreds of miles south and southeast from here. Eventually, it ends at the gates of Tayopopopolis, a massive city in the Unseen Sea.")))
