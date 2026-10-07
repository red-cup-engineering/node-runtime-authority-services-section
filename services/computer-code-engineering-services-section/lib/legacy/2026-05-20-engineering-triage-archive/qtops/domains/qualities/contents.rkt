#lang racket

(require "fillable.rkt")

(provide <>container
         <>contained
         >>make-content-procedures
         >>make-container-procedures
         >contents
         >set-contents!
         >add-contents!
         >add-content!
         >remove-content!
         >search-contents-by-term
         >container
         >set-container!
         >move-thing!!
         >message-container-contents^!
         >message-contents^!)

(define ((>contents t)) (list))
(define ((>set-contents! t) C)
  (t 'set-procedure! 'contents (λ () C)))
(define ((>add-contents! t) C)
  (t 'set-contents! (append (t 'contents) C)))
(define ((>add-content! t) c)
  (t 'add-contents! (list c)))
(define ((>remove-content! t) c)
  (t 'set-contents! (remove c (t 'contents))))
(define ((>search-contents-by-term t) l)
  (filter procedure? (map (λ (q) (when (q 'term=? l) q))
                      (t 'contents))))


(define ((>container t)) (void))
(define ((>set-container! t) c)
  (t 'set-procedure! 'container (λ () c)))

(define ((>move-thing!! t) d)
  (when (and (t 'has-procedure? 'container)
             (procedure? (t 'container)))
    ((t 'container) 'remove-content! t)
        (map
     (λ (n)
       (n 'message! (format "~a moves to: ~a"
                            (if (t 'has-procedure? 'name)
                                (t 'name)
                                "Someone")
                            (if (d 'has-procedure? 'name)
                                (d 'name)
                                "someplace"))))
     (filter procedure?
             (map
              (λ (w)
                (if (w 'has-procedure? 'message!) w #f))
              ((t 'container) 'contents)))))
  (map
   (λ (n)
     (n 'message! (format "~a moves here from: ~a"
                          (if (t 'has-procedure? 'name)
                              (t 'name)
                              "Something")
                          (if (and (t 'has-procedure? 'container)
                                   (procedure? (t 'container))
                                   ((t 'container) 'has-procedure?
                                                   'name))
                              ((t 'container) 'name)
                              "someplace"))))
   (filter procedure?
           (map
            (λ (w)
              (if (w 'has-procedure? 'message!) w #f))
            (d 'contents))))
  (d 'add-content! t)
  (t 'set-container! d))

(define ((>message-container-contents^! t) m)
  (map (λ (t) (when (t 'has-procedure? 'message!)
                (t 'message! m)))
       ((t 'container) 'contents)))

(define ((>message-contents^! t) m)
  (map (λ (t) (when (t 'has-procedure? 'message!)
                (t 'message! m)))
       (t 'contents)))

(define ((>fill-contents! t) c)
  (t 'fill-quality!
      'contents c
      'container >>make-container-procedures
      (λ (w) (w 'move-thing!! t))))

(define (>>make-content-procedures t)
  (log-debug "Making content procedures for ~a" (t 'name))
  (define cp '())
  (define (CP a) (set! cp (append cp a)))
  (define content-procedures '())
  (unless (t 'has-procedure? 'fill-quality!)
    (CP (>>make-fillable-procedures t)))
  (CP
   (list
    (cons 'contents (>contents t))
    (cons 'set-contents! (>set-contents! t))
    (cons 'add-contents! (>add-contents! t))
    (cons 'add-content! (>add-content! t))
    (cons 'remove-content! (>remove-content! t))
    (cons 'search-contents-by-term (>search-contents-by-term t))
    (cons 'message-contents^! (>message-contents^! t))
    (cons 'fill-contents! (>fill-contents! t))))
  cp)

(define (>>make-container-procedures t)
  (log-debug "Making container procedures for ~a" (t 'name))
  (list
   (cons 'container (>container t))
   (cons 'set-container! (>set-container! t))
   (cons 'move-thing!! (>move-thing!! t))
   (cons 'message-container-contents^!
         (>message-container-contents^! t))))

(define (<>container t)
  (t 'set-procedures! (>>make-content-procedures t))
  t)

(define (<>contained t)
  (t 'set-procedures! (>>make-container-procedures t))
  t)
