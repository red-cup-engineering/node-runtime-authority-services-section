#lang racket

(require qtops/qualities/area)

(provide <>engine-room)

(define (<>engine-room t)
  (<>area
   t #:name "engine room"
   #:description "This is the engine room of a ship. It is nondescript except for a series of conducts which come out of the starboard side of the aft bulkhead, run along that plating, and then disappear back into the aft bulkhead near the port bulkhead."))
