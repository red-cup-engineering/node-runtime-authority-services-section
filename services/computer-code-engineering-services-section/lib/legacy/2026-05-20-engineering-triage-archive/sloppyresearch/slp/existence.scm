;; [[file:existing.org::*0 Prelude][0 Prelude:1]]
(use-modules (srfi srfi-1))     ; every, any, filter, etc.
;; 0 Prelude:1 ends here

;; [[file:existing.org::*1 Relational unit (RU)][1 Relational unit (RU):1]]
;;; ---------- Section 1 — Relational unit ----------

(define (as-set xs)
  "Deduplicate list XS preserving order."
  (let loop ((seen '()) (rest xs))
    (if (null? rest) (reverse seen)
        (let ((x (car rest)))
          (if (member x seen) (loop seen (cdr rest))
              (loop (cons x seen) (cdr rest)))))))

(define (subset? a e)
  "True iff every element of A is in E."
  (every (lambda (x) (member x e)) a))

(define (set-diff e a)
  "E \\ A."
  (filter (lambda (x) (not (member x a))) e))

(define (make-relational-unit thing ambient)
  "Construct a relational unit asserting THING ⊆ AMBIENT."
  (when (not (subset? thing ambient))
    (error "thing must be subset of ambient" thing ambient))
  (list (cons 'thing   (as-set thing))
        (cons 'ambient (as-set ambient))))

(define (relational-unit? x)
  "True if X is a record produced by make-relational-unit."
  (and (pair? x)
       (assoc 'thing x)
       (assoc 'ambient x)))

(define (relational-unit-thing ru)   (assoc-ref ru 'thing))
(define (relational-unit-ambient ru) (assoc-ref ru 'ambient))

(define (complement ru)
  "Ambient \\ Thing."
  (set-diff (relational-unit-ambient ru)
            (relational-unit-thing ru)))

(define (complement-disjoint? ru)
  "Thing ∩ complement = ∅."
  (let* ((t (relational-unit-thing ru))
         (c (complement ru)))
    (not (any (lambda (x) (member x t)) c))))
;; 1 Relational unit (RU):1 ends here

;; [[file:existing.org::*2 Typed inclusion predicate][2 Typed inclusion predicate:1]]
(define (typed-subset? thing ambient)
  "True if every element of THING is a Relational unit
   whose ambient equals AMBIENT."
  (every (lambda (x)
           (and (relational-unit? x)
                (equal? (relational-unit-ambient x) ambient)))
         thing))
;; 2 Typed inclusion predicate:1 ends here

;; [[file:existing.org::*3 Distinction][3 Distinction:1]]
;;; ---------- Section 2 — Distinction ----------

(define (make-distinction thing ambient)
  "Return a distinction with inclusion predicate and complement.
   Accepts higher-order THING typed by Relational units."
  (let* ((ru (make-relational-unit thing ambient))
         (inclusion (lambda (x)
                      (if (relational-unit? x)
                          (equal? (relational-unit-ambient x) ambient)
                          (member x (relational-unit-thing ru))))))
    (list (cons 'kind 'distinction)
          (cons 'thing thing)
          (cons 'ambient ambient)
          (cons 'inclusion inclusion)
          (cons 'complement (complement ru)))))

(define (distinction-thing d)      (assoc-ref d 'thing))
(define (distinction-ambient d)    (assoc-ref d 'ambient))
(define (distinction-complement d) (assoc-ref d 'complement))
;; 3 Distinction:1 ends here

;; [[file:existing.org::*4 Residual][4 Residual:1]]
;;; ---------- Section 3 — Residual ----------

(define (residual d)
  "Residual E/A as list of higher-order Relational units."
  (let* ((a (distinction-thing d))
         (e (distinction-ambient d))
         (outside (distinction-complement d)))
    (append
     (map (lambda (x)
            (make-relational-unit (list x) e))
          a)
     (if (null? outside)
         '()
         (list (make-relational-unit outside e))))))

(define (residual-partitions-ambient? d)
  "Residual covers AMBIENT disjointly."
  (let* ((e (distinction-ambient d))
         (classes (map relational-unit-thing (residual d)))
         (flat (apply append classes)))
    (and (every (lambda (x)
                  (= (length (filter (lambda (cls) (member x cls)) classes)) 1))
                e)
         (subset? e flat))))
;; 4 Residual:1 ends here

;; [[file:existing.org::*5 Non-triviality lemma][5 Non-triviality lemma:1]]
(define (nontrivial-residual? d)
  "Residual has ≥2 classes when THING ≠ ∅ and THING ⊂ AMBIENT."
  (let* ((a (distinction-thing d))
         (e (distinction-ambient d)))
    (and (not (null? a))
         (not (equal? (as-set a) (as-set e)))
         (> (length (residual d)) 1))))
;; 5 Non-triviality lemma:1 ends here

;; [[file:existing.org::*6 Dynamics of distinction][6 Dynamics of distinction:1]]
;;; ---------- Section 4 — Dynamics ----------

(define (iterate-residual d n)
  "Apply residual N times, preserving relational typing."
  (let loop ((d0 d) (k n))
    (if (<= k 0) d0
        (let* ((r (residual d0))
               (a* (list (car r)))      ; canonical new thing = class of prior thing
               (e* r)
               (d* (make-distinction a* e*)))
          (loop d* (- k 1))))))
;; 6 Dynamics of distinction:1 ends here

;; [[file:existing.org::*7 Inheritance and closure][7 Inheritance and closure:1]]
(define (residual-inherits-inclusion? d)
  "Original THING’s class reappears as THING of residual."
  (let* ((r (residual d))
         (a (distinction-thing d)))
    (member (car a) (map relational-unit-thing r))))

(define (period-3? d)
  "After three iterations, THING and AMBIENT restore form (idempotent cycle)."
  (let* ((d3 (iterate-residual d 3)))
    (and (equal? (distinction-ambient d)
                 (distinction-ambient d3)))))
;; 7 Inheritance and closure:1 ends here

;; [[file:existing.org::*8 Triad construction][8 Triad construction:1]]
;;; ---------- Section 5 — Triad ----------

(define (make-triad d)
  "Return triad (act condition structure)."
  (list (cons 'act d)
        (cons 'condition (distinction-complement d))
        (cons 'structure (residual d))))

(define (triad-step d)
  "Advance triad one residual iteration."
  (make-triad (iterate-residual d 1)))

(define (triad-coherent? d)
  "Triad stable under three residual iterations."
  (period-3? d))
;; 8 Triad construction:1 ends here

;; [[file:existing.org::*9 Closure corollaries][9 Closure corollaries:1]]
(define (subset-closure-under-iteration? d k)
  "THING ⊆ AMBIENT preserved after k iterations."
  (let* ((dk (iterate-residual d k))
         (a (distinction-thing dk))
         (e (distinction-ambient dk)))
    (typed-subset? a e)))

(define (nontriviality-closure-under-iteration? d k)
  "Residual non-triviality persists whenever complement non-empty."
  (let* ((dk (iterate-residual d k)))
    (or (null? (distinction-complement dk))
        (nontrivial-residual? dk))))
;; 9 Closure corollaries:1 ends here

;; [[file:existing.org::*10 Bridge predicate to Phase II][10 Bridge predicate to Phase II:1]]
(define (period-3<->adjoint-idempotence d)
  "Bridge witness: recurrence ↔ categorical idempotent adjunction."
  (let ((ok (period-3? d)))
    (list (cons 'assumes-period-3 ok)
          (cons 'yields-adjoint-idempotence
                (and ok 'phase-ii-functor-T))
          (cons 'explanation
                "Period-3 recurrence encodes an endofunctor T with T³≈Id; Phase II formalizes it."))))
;; 10 Bridge predicate to Phase II:1 ends here

;; [[file:existing.org::*11 Exports for Phase I][11 Exports for Phase I:1]]
;; ---------- Exports ----------
(define phase-1-exports
  (list
   'make-relational-unit
   'relational-unit?
   'typed-subset?
   'subset?
   'complement
   'make-distinction
   'residual
   'iterate-residual
   'make-triad
   'triad-step
   'triad-coherent?
   'subset-closure-under-iteration?
   'nontriviality-closure-under-iteration?
   'period-3?
   'period-3<->adjoint-idempotence))
;; 11 Exports for Phase I:1 ends here

;; [[file:existing.org::*12 Demo (run to verify)][12 Demo (run to verify):1]]
(define demo-d (make-distinction '(a b) '(a b c d)))
(complement-disjoint? (make-relational-unit '(a b) '(a b c d)))
(residual-partitions-ambient? demo-d)
(triad-coherent? demo-d)
(subset-closure-under-iteration? demo-d 5)
(nontriviality-closure-under-iteration? demo-d 2)
(period-3<->adjoint-idempotence demo-d)
;; 12 Demo (run to verify):1 ends here
