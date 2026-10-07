#lang racket

(require rackunit
         rackunit/text-ui
         (submod "things.rkt" test))

(define l (make-logger 'qtOps-tests))
(define lr (make-log-receiver l 'debug))
(current-logger l)
(thread
 (λ () (let L () (define v (sync lr))
            (printf "~a\n" (vector-ref v 1))
            (L))))


(run-tests (test-suite "All qtMUD tests"
                       qtops-tests:things))
