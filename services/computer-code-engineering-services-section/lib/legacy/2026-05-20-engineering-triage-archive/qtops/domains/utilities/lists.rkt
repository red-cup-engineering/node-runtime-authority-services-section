#lang racket

(provide nth
         random-element)

(define (nth l c)
  (cond
    [(null? l) (raise-argument-error 'nth "index OOB")]
    [(= c 0) (first l)]
    [else (nth (rest l) (- c 1))]))

(define (random-element given-list)
  (list-ref given-list (random (length given-list))))
