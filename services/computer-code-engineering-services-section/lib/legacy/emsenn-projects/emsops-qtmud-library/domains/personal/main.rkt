#lang racket

(require qtops
         qtops/qualities/time
         qtops/qualities/universe
         "../../qualities/document.rkt"
         "../../qualities/emswebserver.rkt"
         "../../qualities/library.rkt"
         "../../qualities/webserver.rkt")

(define ops-log (make-logger 'emsOps))
(define ops-log-receiver (make-log-receiver ops-log 'info))
(current-logger ops-log)
(thread
 (λ ()
   (let l ()
     (define v (sync ops-log-receiver))
     (display (format "~a\n" (vector-ref v 1)))
     (l))))

(define emsverse
  (<>emswebserver
    (<>temporal
     (<>universe (create-thing "emsVerse")))))
(emsverse 'animate~~)
(emsverse 'tick!)
