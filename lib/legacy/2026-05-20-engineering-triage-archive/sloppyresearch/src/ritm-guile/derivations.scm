;; derivations.scm
(define-module (derivations)
  #:use-module (ice-9 pretty-print)
  #:use-module (srfi srfi-1)
  #:export (load-operational-list
            operational-list
            collect-operational-nodes
            extract-names))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Core logic
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define operational-tags '(definition axiom lemma theorem))

(define (load-relational-system path)
  (with-input-from-file path read))

(define (collect-operational-nodes expr)
  (cond
    ((not (list? expr)) '())
    ((null? expr) '())
    (else
     (let* ((head (car expr))
            (tail (cdr expr))
            (self (if (and (symbol? head)
                           (memq head operational-tags))
                      (list expr)
                      '())))
       (append self
               (collect-operational-nodes head)
               (collect-operational-nodes tail))))))

(define (extract-names node)
  (if (and (pair? node)
           (memq (car node) operational-tags))
      (map (lambda (n)
             (if (pair? n)
                 (car n)
                 n))
           (cdr node))
      '()))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Main exported API
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define (load-operational-list filename)
  "Read a relational specification file and return a flat list of operational targets."
  (let* ((data (load-relational-system filename))
         (ops  (collect-operational-nodes data)))
    (apply append (map extract-names ops))))

;; Default behavior if you just import the module
(define operational-list
  (load-operational-list "deriving-existing.scm"))
