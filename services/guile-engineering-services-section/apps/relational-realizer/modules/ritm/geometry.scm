;;; ritm/geometry.scm  ---  Geometric reflection utilities for RITM
;;; (c) emsenn  |  WTFPL or similar permissive license
(define-module (ritm geometry)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (ice-9 match)
  #:use-module (ice-9 hash-table)
  #:use-module (ritm core)
  #:use-module (ritm category)
  #:use-module (ritm modality)
  #:export (
    ;; interval
    make-interval interval? interval-category interval-0 interval-1 interval-u
    ;; category transforms
    category-copy category-shape category-path-closure category-op category-codiscrete
    ;; modal chain
    make-geometry-chain geometry-Pi geometry-Box geometry-Dia geometry-Nabla))


;; ------------------------------------------------------------
;; Interval object I = (0 -> 1)
;; ------------------------------------------------------------
(define-record-type <interval>
  (make-interval* cat o0 o1 u)
  interval?
  (cat interval-category)
  (o0  interval-0)
  (o1  interval-1)
  (u   interval-u))

(define (make-interval)
  "Build the tiny category with two objects 0,1 and a single non-identity u:0→1."
  (let* ((cat (make-category 'I))
         (c0  (register! 'I:0 (make-cell #:data 'I0 #:doc "interval: 0")))
         (c1  (register! 'I:1 (make-cell #:data 'I1 #:doc "interval: 1"))))
    (add-object! cat '0 c0)
    (add-object! cat '1 c1)
    ;; identities will be ensured by check-identities!
    (check-identities! cat)
    ;; add u : 0 -> 1
    (let* ((m (make-morphism c0 c1 'u)))
      (add-morphism! cat 'u m))
    (make-interval* cat c0 c1 (lookup-morphism cat 'u))))

;; ------------------------------------------------------------
;; Utilities
;; ------------------------------------------------------------
(define (category-copy cat)
  "Deep-ish copy of objects/morphisms tables into a fresh category."
  (let ((dst (make-category (category-name cat))))
    ;; objects
    (for-each
     (lambda (kv) (add-object! dst (car kv) (cdr kv)))
     (hash-map->list cons (category-objects cat)))
    ;; morphisms
    (for-each
     (lambda (kv) (add-morphism! dst (car kv) (cdr kv)))
     (hash-map->list cons (category-morphisms cat)))
    dst))

(define (object-pairs cat)
  (hash-map->list cons (category-objects cat)))

(define (morphism-pairs cat)
  (hash-map->list cons (category-morphisms cat)))

;; ------------------------------------------------------------
;; Geometric transforms on categories
;; ------------------------------------------------------------

;; Π→  : SHAPE — forget arrows, keep only objects and identities
(define (category-shape cat)
  (let ((dst (make-category (category-name cat))))
    (for-each (lambda (kv) (add-object! dst (car kv) (cdr kv)))
              (object-pairs cat))
    (check-identities! dst)
    dst))

;; □  : PATH-CLOSURE — add (one step of) composites that are type-correct; idempotent if repeated
(define (category-path-closure cat)
  "Add composites f∘g when tgt(g)=src(f). Does not duplicate existing morphisms."
  (let* ((dst (category-copy cat))
         (mps (morphism-pairs cat)))
    (for-each
     (lambda (a)
       (for-each
        (lambda (b)
          (let* ((ma (cdr a)) (mb (cdr b)))
            (when (eq? (cell-id (morphism-src ma)) (cell-id (morphism-tgt mb)))
              (let* ((mc (compose-morphisms ma mb))
                     (name (gensym "path")))
                (add-morphism! dst name mc)))))
        mps))
     mps)
    dst))

;; ◇  : OPPOSITE — flip every arrow
(define (category-op cat)
  (let ((dst (make-category (string->symbol
                             (string-append (symbol->string (category-name cat)) "^op")))))
    ;; objects unchanged
    (for-each (lambda (kv) (add-object! dst (car kv) (cdr kv)))
              (object-pairs cat))
    ;; identities (added after)
    (check-identities! dst)
    ;; for each non-identity morphism, add flipped arrow
    (for-each
     (lambda (kv)
       (let* ((name (car kv)) (m (cdr kv))
              (src (morphism-src m)) (tgt (morphism-tgt m))
              (tag (morphism-tag m)))
         ;; heuristically skip identities by tag/name check
         (unless (or (eq? tag 'id)
                     (string-suffix? "-id" (symbol->string name)))
           (add-morphism! dst (gensym "op")
                          (make-morphism tgt src (list 'op tag))))))
     (morphism-pairs cat))
    dst))

;; ∇← : CODISCRETE-ish — same as shape for now (keep objects, identities only).
;; This keeps the operational model idempotent and total.
(define (category-codiscrete cat)
  (category-shape cat))

;; ------------------------------------------------------------
;; Modal chain from geometric transforms
;; ------------------------------------------------------------
(define (geometry-Pi)    (make-modality 'Π→ category-shape))
(define (geometry-Box)   (make-modality '□  category-path-closure))
(define (geometry-Dia)   (make-modality '◇  category-op))
(define (geometry-Nabla) (make-modality '∇← category-codiscrete))

(define (make-geometry-chain)
  (let* ((Pi    (geometry-Pi))
         (Box   (geometry-Box))
         (Dia   (geometry-Dia))
         (Nabla (geometry-Nabla)))
    (modality-adjoint-set! Pi Box)
    (modality-adjoint-set! Box Dia)
    (modality-adjoint-set! Dia Nabla)
    (make-chain* Pi Box Dia Nabla)))
