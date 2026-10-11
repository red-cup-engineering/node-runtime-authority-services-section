(define-module (existential-operations)
  #:use-module (derivations)
  #:use-module (ice-9 pretty-print)
  #:export (implementations coverage-report))

;; choose which file to analyze
(define my-ops (load-operational-list "deriving-existing.scm"))

(define implementations (make-hash-table))

(define (implement name func)
  (hash-set! implementations name func))

(implement 'existence (lambda () "Exists, apparently."))
(implement 'coherence (lambda () "Maintains structural integrity."))

(define (coverage-report)
  (let* ((implemented (hash-map->list (lambda (k v) k) implementations))
         (missing (filter (lambda (x)
                            (not (member x implemented)))
                          my-ops)))
    (pretty-print
     (list 'implemented (length implemented)
	   'implemented-list implemented
           'missing (length missing)
           'missing-list missing))))

(coverage-report)
