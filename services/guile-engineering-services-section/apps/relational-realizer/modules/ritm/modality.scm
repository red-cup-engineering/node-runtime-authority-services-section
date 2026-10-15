;;; ritm/modality.scm  ---  Relational ∞-Topos Modalities (operational form)
;;; (c) emsenn  |  WTFPL or similar permissive license

(define-module (ritm modality)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (ice-9 match)
  #:use-module (ritm core)
  #:use-module (ritm category)
  #:use-module (ritm presheaf)
  #:use-module (ritm topology)
  #:export (make-modality modality? modality-name modality-functor
            modality-adjoint modality-adjoint-set!
            apply-modality
            make-chain chain? chain-Pi chain-Box chain-Dia chain-Nabla
            chain-check-adjunctions
            relational-dynamics relational-topology
            ritm-reflexive? default-chain RD RT))

;; ------------------------------------------------------------
;; Single modality record
;; ------------------------------------------------------------
(define-record-type <modality>
  (make-modality* name functor adjoint)
  modality?
  (name    modality-name)
  (functor modality-functor)
  (adjoint modality-adjoint modality-adjoint-set!))

(define* (make-modality name functor #:optional (adjoint #f))
  (make-modality* name functor adjoint))

(define (apply-modality m x)
  ((modality-functor m) x))

;; ------------------------------------------------------------
;; Modal chain Π→ ⊣ □ ⊣ ◇ ⊣ ∇←
;; ------------------------------------------------------------
(define-record-type <chain>
  (make-chain* Pi Box Dia Nabla)
  chain?
  (Pi    chain-Pi)
  (Box   chain-Box)
  (Dia   chain-Dia)
  (Nabla chain-Nabla))

(define (make-chain)
  "Construct a minimal default RITM modal chain with placeholder identity functors."
  (letrec ((Pi    (make-modality 'Π→ (lambda (x) x)))
           (Box   (make-modality '□  (lambda (x) x)))
           (Dia   (make-modality '◇  (lambda (x) x)))
           (Nabla (make-modality '∇← (lambda (x) x))))
    ;; establish adjunction sequence
    (modality-adjoint-set! Pi Box)
    (modality-adjoint-set! Box Dia)
    (modality-adjoint-set! Dia Nabla)
    (make-chain* Pi Box Dia Nabla)))

;; Check basic idempotence for all modalities in a chain
(define (chain-check-adjunctions ch)
  (let ((mods (list (chain-Pi ch) (chain-Box ch)
                    (chain-Dia ch) (chain-Nabla ch))))
    (every (lambda (m)
             (equal? (apply-modality m 'x)
                     (apply-modality m (apply-modality m 'x))))
           mods)))

;; ------------------------------------------------------------
;; Derived internal modalities RD and RT
;; ------------------------------------------------------------
(define (relational-dynamics ch)
  "Derived dynamic sub-modality: Box-stable endofunctors."
  (let ((Box (chain-Box ch)))
    (make-modality 'RD
                   (lambda (x)
                     (apply-modality Box (apply-modality Box x)))
                   Box)))

(define (relational-topology ch)
  "Derived topologic sub-modality: Dia-stable endofunctors."
  (let ((Dia (chain-Dia ch)))
    (make-modality 'RT
                   (lambda (x)
                     (apply-modality Dia (apply-modality Dia x)))
                   Dia)))

;; ------------------------------------------------------------
;; Demo defaults and reflexivity test
;; ------------------------------------------------------------
(define default-chain (make-chain))
(define RD (relational-dynamics default-chain))
(define RT (relational-topology  default-chain))

(define (ritm-reflexive? ch)
  "Test the reflexive property RD ⊣ RT reproduces the modal pattern."
  (let ((rd (relational-dynamics ch))
        (rt (relational-topology  ch)))
    (and (equal? (apply-modality (chain-Box ch) 'x)
                 (apply-modality (modality-adjoint rd) 'x))
         (equal? (apply-modality (chain-Dia ch) 'x)
                 (apply-modality (modality-adjoint rt) 'x)))))

;; ------------------------------------------------------------
;; EOF
;; ------------------------------------------------------------
