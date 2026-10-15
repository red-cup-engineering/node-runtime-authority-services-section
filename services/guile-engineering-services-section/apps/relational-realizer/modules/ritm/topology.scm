;;; ritm/topology.scm  ---  Grothendieck topologies and sheaf conditions
;;; (c) emsenn  |  WTFPL or similar permissive license

(define-module (ritm topology)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (ice-9 match)
  #:use-module (ritm core)
  #:use-module (ritm category)
  #:use-module (ritm presheaf)
  #:export (make-topology topology? topology-category topology-covers
            define-cover! coverings-for
            matching-family? glue! sheaf?))

;; ------------------------------------------------------------
;; topology structure
;; ------------------------------------------------------------
(define-record-type <topology>
  (make-topology* category covers)
  topology?
  (category topology-category)
  ;; covers : hash (object-symbol -> list of cover families)
  (covers topology-covers))

(define (make-topology cat)
  (make-topology* cat (make-hash-table)))

(define (define-cover! topo X-sym morph-list)
  (let* ((table (topology-covers topo))
         (cur   (hash-ref table X-sym '())))
    (hash-set! table X-sym (cons morph-list cur)))
  topo)

(define (coverings-for topo X-sym)
  (hash-ref (topology-covers topo) X-sym '()))

;; ------------------------------------------------------------
;; helpers
;; ------------------------------------------------------------
(define (sym-for-cell cat cell)
  (let ((pairs (hash-map->list cons (category-objects cat))))
    (let loop ((ps pairs))
      (if (null? ps) #f
          (let* ((sym  (caar ps))
                 (val  (cdar ps)))
            (if (eq? (cell-id val) (cell-id cell))
                sym
                (loop (cdr ps))))))))

;; ------------------------------------------------------------
;; matching families & gluing
;; ------------------------------------------------------------

(define* (matching-family? pf cover sections #:key (equal? equal?))
  "SECTIONS is an alist mapping each morphism m : U→X in COVER to s_U ∈ F(U).
   We approximate overlaps by requiring pairwise equality of section values.
   This is a weak matcher—good enough to bootstrap."
  (let loop1 ((xs sections) (ok? #t))
    (cond
     ((or (null? xs) (not ok?))
      ok?)
     (else
      (let loop2 ((ys (cdr xs)) (ok2? ok?))
        (cond
         ((or (null? ys) (not ok2?))
          (loop1 (cdr xs) ok2?))
         (else
          (let ((s1 (cdar xs))
                (s2 (cdar ys)))
            (loop2 (cdr ys) (and ok2? (equal? s1 s2)))))))))))

;; ------------------------------------------------------------
;; gluing
;; ------------------------------------------------------------
(define (glue! pf cover sections)
  "If SECTIONS (alist (m . s_U)) is matching, return their merged value; else #f.
   Current strategy: if all values equal, return that value."
  (if (matching-family? pf cover sections)
      (let ((vals (map cdr sections)))
        (if (and (pair? vals)
                 (every (lambda (x) (equal? x (car vals))) (cdr vals)))
            (car vals)
            #f))
      #f))

;; ------------------------------------------------------------
;; sheaf condition
;; ------------------------------------------------------------
(define* (sheaf? pf topo #:key (equal? equal?))
  "A presheaf is a sheaf if, for each covering family {U_i -> X},
   any matching family of sections s_i ∈ F(U_i) glues uniquely to s ∈ F(X)."
  (let ((cat (presheaf-category pf))
        (ok? #t))
    (for-each
     (lambda (entry)
       (let* ((X-sym  (car entry))
              (covers (coverings-for topo X-sym)))
         (for-each
          (lambda (cover)
            (let* ((sections
                    (map (lambda (m)
                           (let* ((U     (morphism-src m))
                                  (U-sym (sym-for-cell cat U))
                                  (sU    (and U-sym (presheaf-get pf U-sym))))
                             (cons m sU)))
                         cover))
                   (g (glue! pf cover sections)))
              (set! ok?
                    (and ok?
                         (and g
                              (equal? g (presheaf-get pf X-sym)))))))
          covers)))
     (hash-map->list cons (category-objects cat)))
    ok?))

;; ------------------------------------------------------------
;; EOF
;; ------------------------------------------------------------
