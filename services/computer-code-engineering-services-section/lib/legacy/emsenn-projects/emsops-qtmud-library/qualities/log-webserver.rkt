#lang racket

(require qtops/utilities/lists)

(provide <>log-webserver)

(define ((>logs t)) (list))
(define ((>set-logs! t) L)
  (t 'set-procedure! 'logs (λ () L)))
(define ((>add-logs! t) L)
  (t 'set-logs! (append (t 'logs) L)))
(define ((>add-log! t) l)
  (t 'add-logs! (list l)))
(define ((>has-log? t) n)
  (with-handlers ([exn:fail:contract? (λ (e) #f)])
    (when (nth (t 'logs) n) #t)))
(define ((>log t) n)
  (nth (t 'logs) n))

(define ((>log-servlet t) req log-name)
  ((t 'procedure 'xexpr-servlet)
   req
   (if (t 'has-log? (string->number log-name))
       ((t 'procedure 'render-html:page)
        #:title "logs"
        #:content (t 'log (string->number log-name)))
       ((t 'procedure 'render-html:page)
        #:content "No matching logs found."))))


(define ((>log-listing-servlet t) req)
  ((t 'procedure 'xexpr-servlet)
   req
   ((t 'procedure 'render-html:page)
    #:content (string-join (t 'logs)))))

(define (>>make-log-procedures t)
  (list
   (cons 'logs (>logs t))
   (cons 'set-logs! (>set-logs! t))
   (cons 'add-logs! (>add-logs! t))
   (cons 'add-log! (>add-log! t))
   (cons 'has-log? (>has-log? t))
   (cons 'log (>log t))
   (cons 'log-servlet (>log-servlet t))
   (cons 'log-listing-servlet (>log-listing-servlet t))))

(define (<>log-webserver t #:logs [logs #f])
  (t 'set-procedures! (>>make-log-procedures t))
  (when logs (t 'add-logs! logs))
  t)
