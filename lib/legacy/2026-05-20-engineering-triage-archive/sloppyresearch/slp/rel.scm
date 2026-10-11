;; -*- scheme -*-
;; Relational Modality: Posetal and Categorical Construction (Core)
;; Guile module implementing the finite-poset prototype, commuting nuclei,
;; KZ-comonad on a Heyting algebra, factorization, and a tiny “presheaf cell” stub.
;;
;; Model:
;;  - finite Heyting algebra H as a powerset over a finite universe E
;;  - nuclei (closures) and interiors
;;  - relations category on H (posetal) with composition
;;  - KZ-style comonad G = i ∘ c
;;  - two commuting nuclei c_f, c_b induced by a preorder on E
;;  - composites C = i_f ∘ c_b, M = i_b ∘ c_f
;;  - finite stabilization tower over fixpoint families
;;  - minimal “presheaf cell” record with equalizer/coequalizer utilities on finite sets
;;
;; Everything is total on finite inputs. No external dependencies beyond SRFI-1.

(define-module (ritm core)
  #:use-module (srfi srfi-1)          ;; every, find, fold, etc.
  #:use-module (ice-9 hash-table)
  #:export
  ;; Sets over a finite universe
  (make-universe set? empty-set set=?
                 set-in set-insert set-remove set-union set-intersection set-diff
                 set-compl power-set image preimage)
  ;; Heyting algebra over P(E)
  (heyting->implication heyting-negation
   nucleus? make-nucleus apply-nucleus interior-from-closure
   fixpoints)
  ;; Relations category (posetal)
  (rel-id rel-comp rel-morphism?)
  ;; KZ-comonad G = i ∘ c
  (G-comonad make-G epsilon-delta coalgebra?)
  ;; Preorders and induced nuclei
  (make-preorder up-closure down-closure
   c-forward c-backward interiors-forward-backward
   C-composite M-composite commute?)
  ;; Orthogonal-like factorization (posetal)
  (C-stable? M-stable? factorize-CM subset?)
  ;; Transfinite (finite) closure tower
  (closure-tower tower-stabilize)
  ;; Tiny “presheaf cell” stubs
  (make-pcell pcell-a_f pcell-a_b pcell-i_f pcell-i_b
              pcell-Pi_f pcell-Pi_b
              pcell-Box pcell-Diamond pcell-BoxDiamond pcell-DiamondBox))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Utility: finite sets as lists without duplicates (universe-scoped)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define (uniq xs)
  (let loop ((seen '()) (rest xs))
    (if (null? rest) (reverse seen)
        (let ((x (car rest)))
          (if (member x seen) (loop seen (cdr rest))
              (loop (cons x seen) (cdr rest)))))))

(define (make-universe elems)
  (let ((U (uniq elems)))
    (define (ensure-subset s)
      (for-each
       (lambda (x)
         (unless (member x U)
           (error "Element not in universe" x U)))
       s)
      (uniq s))
    (define (set? s)
      (and (list? s) (every (lambda (x) (member x U)) s)))
    (define (empty-set) '())
    (define (set=? a b)
      (and (every (lambda (x) (member x b)) a)
           (every (lambda (x) (member x a)) b)))
    (define (set-in x s) (member x s))
    (define (set-insert x s) (if (member x s) s (cons x s)))
    (define (set-remove x s) (filter (lambda (y) (not (equal? x y))) s))
    (define (set-union . ss) (uniq (apply append ss)))
    (define (set-intersection a b) (filter (lambda (x) (member x b)) a))
    (define (set-diff a b) (filter (lambda (x) (not (member x b))) a))
    (define (set-compl a) (set-diff U a))
    (define (power-set)
      (let loop ((xs U))
        (if (null? xs) (list '())
            (let* ((p (loop (cdr xs)))
                   (x (car xs)))
              (append p (map (lambda (s) (cons x s)) p))))))
    (define (image f s) (uniq (map f s)))
    (define (preimage f s) (filter (lambda (x) (member (f x) s)) U))
    (values U set? ensure-subset empty-set set=? set-in set-insert set-remove
            set-union set-intersection set-diff set-compl power-set image preimage)))

;; Heyting implication and negation on P(E)
(define (heyting->implication set-compl set-union)
  (lambda (A B) (set-union (set-compl A) B)))

(define (heyting-negation set-compl)
  (lambda (A) (set-compl A)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Nuclei (closures) and interiors on P(E)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; nucleus? : (c : P(E)->P(E)) -> check axioms (inflationary, idempotent, monotone, meet-preserving)
;; Complexity: O(|P(E)|^2) passes; intended only for small finite universes.
(define (nucleus? c subsets set-union set-intersection set=?)
  (let* ((ps subsets)
         (pairs (apply append
                       (map (lambda (a) (map (lambda (b) (list a b)) ps)) ps))))
    (and
     ;; inflationary: a <= c(a)
     (every (lambda (a) (every (lambda (x) (member x (c a))) a)) ps)
     ;; idempotent: c(c(a)) = c(a)
     (every (lambda (a) (set=? (c (c a)) (c a))) ps)
     ;; monotone: a<=b => c(a)<=c(b)
     (every (lambda (pr)
              (let ((a (car pr)) (b (cadr pr)))
                (if (every (lambda (x) (member x b)) a)
                    (every (lambda (x) (member x (c b))) (c a))
                    #t)))
            pairs)
     ;; meet-preserving: c(a∧b) = c(a) ∧ c(b)
     (every (lambda (pr)
              (let* ((a (car pr)) (b (cadr pr))
                     (lhs (c (set-intersection a b)))
                     (rhs (set-intersection (c a) (c b))))
                (set=? lhs rhs)))
            pairs))))

(define (make-nucleus c) c)
(define (apply-nucleus c A) (c A))

(define (interior-from-closure c set-compl)
  (lambda (A) (set-compl (c (set-compl A)))))

(define (fixpoints c subsets set=?)
  (filter (lambda (a) (set=? (c a) a)) subsets))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Relations category (posetal form)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; Objects: elements a of H (subsets of E).
;; Morphisms a→b: elements r below (a ⇒ b).
;; Identity: id_a = (a ⇒ a) = ⊤. Composition (s ∘ r) = r ∧ (a ⇒ s).
(define (rel-id impl a) (impl a a))

(define (rel-morphism? r a b impl subset?)
  ;; Check r ⊆ (a ⇒ b)
  (subset? r (impl a b)))

(define (rel-comp r s a impl set-intersection)
  ;; s ∘ r = r ∩ (a ⇒ s)
  (set-intersection r (impl a s)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; KZ-style comonad G = i ∘ c on the poset
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define (make-G closure interior)
  (lambda (A) (interior (closure A))))

;; epsilon-delta provide inequalities G A ⊆ A (counit) and G A ⊆ G G A (comultiplication)
(define (epsilon-delta G closure interior subset?)
  (values
   (lambda (A) (subset? (G A) A))            ;; ε_A: G A ⊆ A
   (lambda (A) (subset? (G A) (G (G A))))))  ;; δ_A: G A ⊆ G G A

;; Alias for export name
(define G-comonad make-G)

;; coalgebra? : posetal check whether A ⊆ G A
(define (coalgebra? A G subset?)
  (subset? A (G A)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Preorders on E and induced closure nuclei (up/down-closures)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define (make-preorder universe leq?)  ;; leq? : E x E -> boolean (reflexive, transitive expected)
  (values universe leq?))

(define (up-closure universe leq? set-union)
  (lambda (U)
    (let loop ((front U) (seen '()))
      (if (null? front) (uniq seen)
          (let* ((x (car front))
                 (up (filter (lambda (y) (leq? x y)) universe))
                 (new (set-union up seen)))
            (loop (cdr front) new))))))

(define (down-closure universe leq? set-union)
  (lambda (U)
    (let loop ((front U) (seen '()))
      (if (null? front) (uniq seen)
          (let* ((x (car front))
                 (down (filter (lambda (y) (leq? y x)) universe))
                 (new (set-union down seen)))
            (loop (cdr front) new))))))

;; Forward/backward nuclei from a preorder
(define (c-forward upc) upc)
(define (c-backward downc) downc)

(define (interiors-forward-backward cf cb set-compl)
  (values (interior-from-closure cf set-compl)
          (interior-from-closure cb set-compl)))

(define (C-composite ifrom cb)   ;; C = i_f ∘ c_b
  (lambda (A) (ifrom (cb A))))

(define (M-composite iback cf)   ;; M = i_b ∘ c_f
  (lambda (A) (iback (cf A))))

(define (commute? cf cb subsets set=?)
  (every (lambda (a) (set=? (cf (cb a)) (cb (cf a)))) subsets))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Orthogonal-like factorization (posetal, C-stable/M-stable)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

(define (subset? A B)        ;; A ⊆ B
  (every (lambda (x) (member x B)) A))

(define (C-stable? x y C subset?)
  (subset? x (C y)))

(define (M-stable? x y M subset?)
  (subset? (M x) y))

;; factorize-CM : returns (values left mid right C-ok? M-ok?)
(define (factorize-CM x y C M subset?)
  (let ((mid (C y)))
    (values x mid y (C-stable? x y C subset?) (M-stable? mid y M subset?))))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Closure tower (finite stabilization over fixpoint families)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; closure-tower: iterate a list of nuclei cyclically until the family of fixpoints stabilizes.
;; Returns the sequence of fixpoint families [H0, H1, ...] and the index where stabilized.
(define (closure-tower nuclei subsets set=?)
  (let loop ((Hs (list subsets)) (idx 0))
    (let* ((c (list-ref nuclei (modulo idx (length nuclei))))
           (fix (fixpoints c (car Hs) set=?)))
      (if (and (pair? Hs)
               (let ((prev (car Hs)))
                 (and (= (length prev) (length fix))
                      (every (lambda (a) (member a fix)) prev)
                      (every (lambda (a) (member a prev)) fix))))
          (values (reverse Hs) idx)
          (loop (cons fix Hs) (+ idx 1))))))

;; tower-stabilize: convenience wrapper
(define (tower-stabilize nuclei subsets set=?)
  (closure-tower nuclei subsets set=?))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Minimal “presheaf cell” over the arrow category 0 -> 1 (finite sets)
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;

;; Represent a presheaf X as:
;;  X0 : set of elements at 0
;;  X1 : set of elements at 1
;;  u* : function X1 -> X0  (total, given as procedure or association list)

(define (func-apply f* x)
  (cond
   ((procedure? f*) (f* x))
   ((list? f*) (let ((p (assoc x f*))) (and p (cdr p))))
   (else (error "u* must be procedure or alist" f*))))

(define (make-pcell X0 X1 u-star) (list X0 X1 u-star))
(define (pcell-X0 P) (list-ref P 0))
(define (pcell-X1 P) (list-ref P 1))
(define (pcell-u* P) (list-ref P 2))

;; Equalizer of the parallel pair (u*, g*): subset of X1 where u*(x)=g*(x).
(define (equalizer-X1 X1 f* g*)
  (filter (lambda (x) (equal? (func-apply f* x) (func-apply g* x))) X1))

;; Coequalizer of f*, g*: X1 -> X0 as quotient on X0 by relation f*(x) ~ g*(x).
;; Returns: (values representatives rep-of) where rep-of maps any x0∈X0 to its class representative.
(define (coequalize-X0-with-map X0 X1 f* g*)
  (let* ((parent (make-hash-table))
         (find-rep (lambda (x)
                     (let loop ((y x))
                       (let ((p (hash-ref parent y #f)))
                         (if (and p (not (equal? p y))) (loop p) y)))))
         (union! (lambda (a b)
                   (let ((ra (find-rep a)) (rb (find-rep b)))
                     (unless (equal? ra rb) (hash-set! parent ra rb))))))
    ;; initialize parent pointers
    (for-each (lambda (x) (hash-set! parent x x)) X0)
    ;; union pairs induced by parallel arrows
    (for-each (lambda (x1)
                (let ((a (func-apply f* x1))
                      (b (func-apply g* x1)))
                  (when (and a b) (union! a b))))
              X1)
    ;; build classes and representative set
    (let* ((classes (make-hash-table))
           (_ (for-each (lambda (x0)
                          (let ((r (find-rep x0)))
                            (hash-set! classes r (cons x0 (hash-ref classes r '())))))
                        X0))
           (reps (hash-map->list (lambda (k v) k) classes))
           (rep-of (lambda (x0) (find-rep x0))))
      (values reps rep-of)))

;; a_f: (X0, X1, u*) |-> coequalizer on X0 of (u*, g*). Default g* is constant to first X0 if present.
(define (pcell-a_f P . maybe-g*)
  (let* ((X0 (pcell-X0 P))
         (X1 (pcell-X1 P))
         (u* (pcell-u* P))
         (g* (if (null? maybe-g*)
                 (if (null? X0)
                     (lambda (x) #f)
                     (let ((c (car X0))) (lambda (x) c)))
                 (car maybe-g*))))
    (call-with-values
        (lambda () (coequalize-X0-with-map X0 X1 u* g*))
      (lambda (q rep-of)
        (list q
              X1
              ;; new u*: X1 -> q sends each x1 to the representative of u*(x1)
              (lambda (x1)
                (let ((ux (func-apply u* x1)))
                  (and ux (rep-of ux)))))))))

;; a_b: (X0, X1, u*) |-> equalizer on X1 of (u*, g*). Default g* = u* so eq = X1.
(define (pcell-a_b P . maybe-g*)
  (let* ((X0 (pcell-X0 P))
         (X1 (pcell-X1 P))
         (u* (pcell-u* P))
         (g* (if (null? maybe-g*) u* (car maybe-g*))))
    (list X0
          (equalizer-X1 X1 u* g*)
          ;; restricted u* to the equalizer subset
          (lambda (x1) (func-apply u* x1)))))

;; i_f / i_b: inclusions are identity-on-components in this finite model
(define (pcell-i_f P) P)
(define (pcell-i_b P) P)

;; Right adjoints Π_f / Π_b — placeholders in this tiny model.
(define (pcell-Pi_f P) P)
(define (pcell-Pi_b P) P)

;; Modalities Box=i_f, Diamond=i_b and composites
(define (pcell-Box P) (pcell-i_f P))
(define (pcell-Diamond P) (pcell-i_b P))
(define (pcell-BoxDiamond P) (pcell-Box (pcell-Diamond P)))
(define (pcell-DiamondBox P) (pcell-Diamond (pcell-Box P)))

;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
;; Example wiring (usage sketch in REPL, not exported)
;;
;; (define-values (E set? ensure empty =? in insert remove ∪ ∩ \ ~ pow img pre)
;;   (make-universe '(0 1 2)))
;; (define ⇒ (heyting->implication ~ ∪))
;; (define neg (heyting-negation ~))
;; (define-values (_ ≤?) (make-preorder E (lambda (x y) (<= x y))))
;; (define upc (up-closure E ≤? ∪))
;; (define downc (down-closure E ≤? ∪))
;; (define if (interior-from-closure upc ~))
;; (define ib (interior-from-closure downc ~))
;; (define C (C-composite if downc))
;; (define M (M-composite ib upc))
;; (commute? upc downc (pow) =?)
;; (define G (make-G upc if))
;; (define εδ (epsilon-delta G upc if subset?))
;; (call-with-values (lambda () εδ) (lambda (ε δ) (ε '(0)) (δ '(0))))
;;
;; End of module
;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;;
