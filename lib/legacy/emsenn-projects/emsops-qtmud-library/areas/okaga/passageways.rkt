#lang racket

(require qtops/qualities/area)

(provide <>fore-passageway
         <>aft-passageway)

(define (<>fore-passageway t)
  (<>area
    t #:name "fore passageway"
    #:description "This is the fore passageway of a ship. The bulkheads and deck plating are all made of the same grey metal."))

(define (<>aft-passageway t)
  (<>area
    t #:name "aft passageway"
    #:description "This is the aft passageway of a ship."))
