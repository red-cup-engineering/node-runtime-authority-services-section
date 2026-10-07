#lang racket

(require qtops/qualities/area
         qtops/qualities/noise)

(provide <>airlock)

(define (<>airlock t)
  (<>noisy
   (<>area
    t #:name "airlock"
    #:description "This is the airlock of a ship, with exits to port and starboard, on- and out-board respectively. Right now, the port airlock is open, and the starboard airlock is sealed.")
   #:noises '("A panel on the bulkhead to fore flashes green for a moment.")
   #:frequency (λ () (random 1300 2000))))
