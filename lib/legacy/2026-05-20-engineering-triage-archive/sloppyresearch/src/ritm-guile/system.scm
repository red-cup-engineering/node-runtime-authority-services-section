;; system.scm
(define-module (relational-system)
  #:use-module (ice-9 pretty-print)
  #:use-module (derivations)
  #:export (handwritten-foundations
            formal-foundations
            derivations
            codebases
            foundation
            list-foundations
            load-foundation
            precedence-order))

(define handwritten-foundations
  (cons 'handwritten-foundations "deriving-existing.scm"))
(define formal-foundations
  (cons 'formal-foundations "deriving-reflexive-existence.scm"))

(define derivations
  (list handwritten-foundations
        formal-foundations))
(define precedence-order
  (map car derivations))

(define (foundation label)
  "Return the path associated with a foundation label."
  (let ((found (assoc label derivations)))
    (if found
        (cdr found)
        (error "Unknown foundation label" label))))

(define (load-foundation label)
  "Load the relational system (S-expressions) of a given foundation."
  (load-relational-system (foundation label)))

(define (list-foundations)
  (pretty-print
   (map (lambda (p) (list (car p) "→" (cdr p))) derivations)))

;; --- Codebases (extendable registry) ---------------------------------------

(define codebases
  (list
   (cons 'derivations derivations))) 
