#lang racket

(require qtops
         qtops/qualities/animation)

(provide <>harvestable)

(define (>>make-harvestable-procedures t)
  (log-debug "Making harvestable procedures for ~a"
             (t 'name))
  (list
   (cons 'harvestable? (λ () #t))
   (cons 'set-harvestable?!
         (λ (v)
           (t 'set-procedure! 'harvestable?
              (λ () v))))
   (cons 'harvest-description
         (λ () "Something can be harvested from this."))
   (cons 'set-harvest-description!
         (λ (l) (t 'set-procedure! 'harvest-description
                   (λ () l))))
   (cons 'harvest-frequency
         (λ () 16000))
   (cons 'set-harvest-frequency!
         (λ (f) (t 'set-procedure! 'harvest-frequency
                   (λ () f))))
   (cons 'harvest-return (λ () (void)))
   (cons 'set-harvest-return!
         (λ (v)
           (t 'set-procedure! 'harvest-return
              (λ () v))))
   (cons 'harvest!
         (λ (w)
           (define r
             ((t 'harvest-return)
              (if (t 'has-procedure? 'create-thing-^!)
                  (t 'create-thing^!)
                  (if (and (t 'has-procedure? 'universe)
                           ((t 'universe) 'has-procedure?
                                          'create-thing!))
                      ((t 'universe) 'create-thing!)
                      (create-thing)))))
           (w 'add-content! r)
           (w 'message! (format "You harvest ~a from ~a"
                                (r 'name) (t 'name)))
           (t 'set-harvestable?! #f)
           (t 'set-procedure!
              'restock
              (λ ()
                (t 'set-harvestable?! #t)
                (t 'remove-animation! 'restock)))
           (t 'add-animation! `(restock ,(t 'harvest-frequency) 100))
           (t 'animate~~)))))

(define (<>harvestable t
                       #:return [return #f]
                       #:frequency [frequency #f])
  (unless (t 'has-procedure? 'animations)
    (t 'set-procedures! (>>make-animation-procedures t)))
  (t 'set-procedures! (>>make-harvestable-procedures t))
  (when return (t 'set-harvest-return! return))
  (when frequency (t 'set-harvest-frequency! frequency)))
