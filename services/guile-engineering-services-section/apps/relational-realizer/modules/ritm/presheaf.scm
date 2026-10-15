;;; ritm/presheaf.scm  ---  Presheaves and Natural Transformations
;;; (c) emsenn | WTFPL or similar permissive license

(define-module (ritm presheaf)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (ice-9 match)
  #:use-module (ice-9 hash-table)
  #:use-module (ritm core)
  #:use-module (ritm category)
  #:export
  ;; presheaf core
  (make-presheaf presheaf? presheaf-category presheaf-restrict-proc
   presheaf-sections presheaf-sections-set!
   presheaf-set! presheaf-get presheaf-restrict
   check-presheaf-identity-law! check-presheaf-composition-law!
   ;; natural transformations
   make-nattrans nattrans? nattrans-src nattrans-tgt
   nattrans-component nattrans-apply check-naturality!
   ;; convenience
   make-constant-presheaf
   space->doc-presheaf))

;; ------------------------------------------------------------
;; Presheaf F : C^op -> Set
;; ------------------------------------------------------------
(define-record-type <presheaf>
  (make-presheaf* category restrict-proc sections)
  presheaf?
  (category presheaf-category)
  ;; restrict-proc : (lambda (pf morph value-at-target) -> value-at-source)
  (restrict-proc presheaf-restrict-proc)
  ;; sections: hash (object-symbol -> value)
  (sections presheaf-sections presheaf-sections-set!))

(define* (make-presheaf cat #:key (restrict-proc (lambda (pf m v) v)))
  "Create a presheaf on category CAT.
   RESTRICT-PROC gets (pf morph value-at-target) and must return a value on source."
  (make-presheaf* cat restrict-proc (make-hash-table)))

;; Set and get a section at an object (by its symbol name).
(define (presheaf-set! pf obj-sym value)
  (hash-set! (presheaf-sections pf) obj-sym value)
  pf)

(define (presheaf-get pf obj-sym)
  (hash-ref (presheaf-sections pf) obj-sym #f))

;; Apply F(f) contravariantly: value at tgt -> value at src
(define (presheaf-restrict pf morph value-at-tgt)
  ((presheaf-restrict-proc pf) pf morph value-at-tgt))

;; ------------------------------------------------------------
;; Functoriality sanity checks (property-based over given samples)
;; ------------------------------------------------------------
(define* (check-presheaf-identity-law! pf samples #:key (equal? equal?))
  "samples: alist of (obj-sym . sample-value). Checks F(id_X)(s) = s."
  (let ((ok? #t))
    (for-each
     (lambda (pair)
       (let* ((obj-sym (car pair))
              (sample (cdr pair))
              (cell   (lookup-object (presheaf-category pf) obj-sym)))
         (when cell
           (let* ((id   (id-morphism cell))
                  (rest (presheaf-restrict pf id sample)))
             (set! ok? (and ok? (equal? rest sample)))))))
     samples)
    ok?))

(define* (check-presheaf-composition-law! pf triples #:key (equal? equal?))
  "triples: list of (m1 m2 s) where m1 ∘ m2 is composable and s is a section at tgt(m2).
   Checks F(m1 ∘ m2)(s) = F(m2)(F(m1)(s)) contravariantly."
  (let ((ok? #t))
    (for-each
     (lambda (tr)
       (match tr
         ((m1 m2 s)
          (catch #t
            (lambda ()
              (let* ((comp (compose-morphisms m1 m2))
                     ;; contravariant: F(comp) s  vs  F(m2)(F(m1) s)
                     (lhs (presheaf-restrict pf comp s))
                     (mid (presheaf-restrict pf m1 s))
                     (rhs (presheaf-restrict pf m2 mid)))
                (set! ok? (and ok? (equal? lhs rhs)))))
            (lambda args (set! ok? #f))))))
     triples)
    ok?))

;; ------------------------------------------------------------
;; Natural transformations η : F ⇒ G (components η_X : F(X) → G(X))
;; ------------------------------------------------------------
(define-record-type <nattrans>
  (make-nattrans* src tgt component)
  nattrans?
  (src nattrans-src)
  (tgt nattrans-tgt)
  ;; component : (lambda (obj-sym value-in-FX) -> value-in-GX)
  (component nattrans-component))

(define (make-nattrans F G component)
  (make-nattrans* F G component))

(define (nattrans-apply eta obj-sym value-in-F)
  ((nattrans-component eta) obj-sym value-in-F))

(define* (check-naturality! eta morph #:key (equal? equal?))
  "Check G(m) ∘ η_Y = η_X ∘ F(m) for morph : X <- Y (remember presheaves are contravariant).
   Returns #t if the square commutes for currently stored sections at Y."
  (let* ((F (nattrans-src eta))
         (G (nattrans-tgt eta))
         (src-cell (morphism-src morph))
         (tgt-cell (morphism-tgt morph)))
    (define (sym-for-cell cat cell)
      (let ((pairs (hash-map->list cons (category-objects cat))))
        (let loop ((ps pairs))
          (if (null? ps) #f
              (let* ((sym (caar ps))
                     (val (cdar ps)))
                (if (eq? (cell-id val) (cell-id cell)) sym
                    (loop (cdr ps))))))))
    (let* ((cat (presheaf-category F))
           (X-sym (sym-for-cell cat src-cell))
           (Y-sym (sym-for-cell cat tgt-cell))
           (sY   (presheaf-get F Y-sym)))
      (if (not sY)
          #t
          (let* ((left  (presheaf-restrict G morph (nattrans-apply eta Y-sym sY)))
                 (right (nattrans-apply eta X-sym (presheaf-restrict F morph sY))))
            (equal? left right))))))

;; ------------------------------------------------------------
;; Convenience presheaves
;; ------------------------------------------------------------
(define (make-constant-presheaf cat value)
  "Δ(value): assigns the same VALUE to every object; all restrictions are identity."
  (let ((pf (make-presheaf cat #:restrict-proc (lambda (pf morph val) val))))
    ;; initialize each object with VALUE
    (for-each
     (lambda (kv)
       (presheaf-set! pf (car kv) value))
     (hash-map->list cons (category-objects cat)))
    pf))

(define (space->doc-presheaf sp)
  "Interpret a space as a category and return a presheaf of documentation strings over it.
   For each binding symbol x, F(x) is the doc string for that value; restrictions are identity."
  (let* ((cat (space->category sp))
         (pf  (make-presheaf cat #:restrict-proc (lambda (pf morph s) s))))
    ;; populate using doc-of from (ritm core)
    (for-each
     (lambda (kv)
       (let* ((sym (car kv))
              (val (cdr kv))
              (doc (doc-of val)))
         (presheaf-set! pf sym doc)))
     (hash-map->list cons (category-objects cat)))
    pf))

;; ------------------------------------------------------------
;; EOF
;; ------------------------------------------------------------
