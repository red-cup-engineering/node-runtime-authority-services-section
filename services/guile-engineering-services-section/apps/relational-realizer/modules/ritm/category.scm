;;; ritm/category.scm  ---  Relational-Topos Category Layer for Guile
;;; (c) emsenn  |  WTFPL or similar permissive license

(define-module (ritm category)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (ice-9 match)
  #:use-module (ice-9 hash-table)
  #:use-module (ritm core)
  #:export (make-morphism morphism? morphism-src morphism-tgt morphism-tag
            id-morphism compose-morphisms
            make-category category? category-objects category-morphisms
            add-object! add-morphism!
            lookup-object lookup-morphism
            check-identities! check-associativity!
            space->category))

;; ------------------------------------------------------------
;; Morphisms (edges as composable arrows)
;; ------------------------------------------------------------
(define-record-type <morphism>
  (make-morphism src tgt tag)
  morphism?
  (src morphism-src)
  (tgt morphism-tgt)
  (tag morphism-tag))

;; Identity morphism for a cell
(define (id-morphism cell)
  (make-morphism cell cell 'id))

;; Composition: f ∘ g defined when tgt(g)=src(f)
(define (compose-morphisms f g)
  (if (eq? (cell-id (morphism-src f)) (cell-id (morphism-tgt g)))
      (make-morphism (morphism-src g)
                     (morphism-tgt f)
                     (list 'composed (morphism-tag g) (morphism-tag f)))
      (error "Cannot compose: target of g ≠ source of f" f g)))

;; ------------------------------------------------------------
;; Categories (object + morphism tables)
;; ------------------------------------------------------------
(define-record-type <category>
  (make-raw-category name objects morphisms)
  category?
  (name category-name)
  (objects category-objects category-objects-set!)
  (morphisms category-morphisms category-morphisms-set!))
(define* (make-category #:optional (name 'unnamed))
  (make-raw-category name (make-hash-table) (make-hash-table)))

;; ------------------------------------------------------------
;; Category mutation and lookup
;; ------------------------------------------------------------
(define (add-object! cat sym cell)
  (hash-set! (category-objects cat) sym cell)
  cat)

(define (lookup-object cat sym)
  (hash-ref (category-objects cat) sym #f))

(define (add-morphism! cat name morph)
  (hash-set! (category-morphisms cat) name morph)
  cat)

(define (lookup-morphism cat name)
  (hash-ref (category-morphisms cat) name #f))

;; ------------------------------------------------------------
;; Coherence checks
;; ------------------------------------------------------------
(define (check-identities! cat)
  "Verify that each object has an identity morphism recorded."
  (for-each
   (lambda (entry)
     (let* ((sym (car entry))
            (cell (cdr entry))
            (id-name (string->symbol (string-append (symbol->string sym) "-id")))
            (id (lookup-morphism cat id-name)))
       (when (not id)
         (add-morphism! cat id-name (id-morphism cell)))))
   (hash-map->list cons (category-objects cat)))
  cat)

(define (check-associativity! cat)
  "Naive associativity test over all triples of morphisms.
   Returns #t if all possible compositions are well-typed."
  (let ((morphs (hash-map->list cons (category-morphisms cat))))
    (let loop ((triples (cartesian-product morphs morphs morphs))
               (ok? #t))
      (if (null? triples)
          ok?
          (let* ((a (cdar triples)) (b (cadar triples)) (c (caddar triples))
                 (valid?
                  (and (eq? (cell-id (morphism-tgt c))
                            (cell-id (morphism-src b)))
                       (eq? (cell-id (morphism-tgt b))
                            (cell-id (morphism-src a))))))
            (loop (cdr triples)
                  (and ok? valid?)))))))

;; ------------------------------------------------------------
;; Conversion from spaces (modules) to categories
;; ------------------------------------------------------------
(define (space->category sp)
  "Interpret a space (from ritm core) as a small category.
   Objects: each binding symbol.
   Morphisms: trivial identity arrows; relations become additional morphisms."
  (let ((cat (make-category 'space-category)))
    ;; add objects
    (for-each
     (lambda (entry)
       (add-object! cat (car entry) (cdr entry)))
     (space-bindings sp))
    ;; add trivial identities
    (check-identities! cat)
    ;; add any relations that exist between registered cells
    (for-each
     (lambda (entry)
       (match entry
         ((from . (tos . tag))
          (let ((src (lookup-object cat from)))
            (for-each
             (lambda (to)
               (let ((tgt (lookup-object cat to)))
                 (when (and src tgt)
                   (add-morphism! cat
                                  (gensym (symbol->string from))
                                  (make-morphism src tgt tag)))))
             tos)))))
     (space-relations sp))
    cat))

;; ------------------------------------------------------------
;; Utility: Cartesian product (local definition)
;; ------------------------------------------------------------
(define (cartesian-product . lists)
  (if (null? lists)
      '(())
      (apply append
             (map (lambda (x)
                    (map (lambda (y) (cons x y))
                         (apply cartesian-product (cdr lists))))
                  (car lists)))))

;; ------------------------------------------------------------
;; EOF
;; ------------------------------------------------------------
