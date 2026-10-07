#lang racket

(provide <>trivial
         >>make-trivia-procedures
         >trivia
         >set-trivia!
         >add-trivia!
         >add-trivium!
         >remove-trivium!)

(define ((>trivia t)) (list))
(define ((>set-trivia! t) C)
  (t 'set-procedure! 'trivia (λ () C)))
(define ((>add-trivia! t) C)
  (t 'set-trivia! (append (t 'trivia) C)))
(define ((>add-trivium! t) c)
  (t 'add-trivia! (list c)))
(define ((>remove-trivium! t) c)
  (t 'set-trivia! (remove c (t 'trivia))))


(define (>>make-trivia-procedures t)
  (list
   (cons 'trivia (>trivia t))
   (cons 'set-trivia! (>set-trivia! t))
   (cons 'add-trivia! (>add-trivia! t))
   (cons 'add-trivium! (>add-trivium! t))
   (cons 'remove-trivium! (>remove-trivium! t))))

(define (<>trivial t #:trivia [trivia #f])
  (t 'set-procedures! (>>make-trivia-procedures t))
  (when trivia (t 'add-trivia! trivia)))
