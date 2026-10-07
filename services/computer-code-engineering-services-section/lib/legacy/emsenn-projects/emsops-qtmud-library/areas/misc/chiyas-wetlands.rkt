#lang racket

(require qtops/qualities/area
         qtops/qualities/lookable)

(provide <>wetlands)

(define (<>trees t)
  (<>lookable
    t #:name "ramin trees"
    #:description "Thick-trunked trees stretch upward from the ground, some maybe 60 or 70 meters tall. The trunks are covered in long horizontal strips of thick red bark, which has fallen in places. In other places, its been covered over by a thick moss."
    #:adjectives '("thick-trunked" "thick" "tall" "mossy" "ramin")))

(define (<>wetlands t)
  (<>area
    t #:name "wetlands"
    #:description  "Ramin trees nearly competely shadow the ground here, a dark brown humus tinged with red. There are a few small pools of black water, churning invisibly with life."
    #:contents (list <>trees)))
