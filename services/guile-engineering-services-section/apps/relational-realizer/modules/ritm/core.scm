;;; ritm.scm  ---  minimal relational-topos runtime for Guile
;;; (c) emsenn  |  WTFPL or similar permissive license

(define-module (ritm core)
  #:use-module (srfi srfi-1)
  #:use-module (srfi srfi-9)
  #:use-module (ice-9 match)
  #:use-module (ice-9 hash-table)
  #:use-module (system base pmatch)
  #:export (make-cell cell? cell-id cell-data cell-data-set! cell-doc cell-doc-set!
            relate! relations-of neighbors
            register! resolve registered-symbols
            doc! doc-of
            module->space space? space-bindings space-relations space->alist
            set-updater! step! tick!))

;; ------------------------------------------------------------
;; Cells
;; ------------------------------------------------------------
(define-record-type <cell>
  (make-raw-cell id data doc updater)
  cell?
  (id      cell-id)
  (data    cell-data cell-data-set!)
  (doc     cell-doc  cell-doc-set!)
  (updater cell-updater cell-updater-set!))

;; Guile supports keyword args via define*
(define* (make-cell #:key (data #f) (doc "") (updater #f))
  (make-raw-cell (gensym "cell") data doc updater))

;; ------------------------------------------------------------
;; Documentation table (side-channel presheaf)
;; ------------------------------------------------------------
(define %doc-table (make-hash-table))

(define-syntax-rule (doc! value string)
  (begin
    (hashq-set! %doc-table value (if (string? string)
                                     string
                                     (object->string string)))
    value))

(define (doc-of value)
  (hashq-ref %doc-table value ""))

;; ------------------------------------------------------------
;; Relations (edges in the quiver)
;; ------------------------------------------------------------
(define %edges (make-hash-table)) ; id -> list of (to-id . tag)

(define (relate! from-cell to-cell tag)
  (let* ((fid (cell-id from-cell))
         (tid (cell-id to-cell))
         (lst (hashq-ref %edges fid '())))
    (hashq-set! %edges fid (acons tid tag lst))
    (values from-cell to-cell tag)))

(define (relations-of cell)
  (hashq-ref %edges (cell-id cell) '()))

(define (neighbors cell)
  (map car (relations-of cell)))

;; ------------------------------------------------------------
;; Registry (symbol → cell)
;; ------------------------------------------------------------
(define %registry (make-hash-table))

(define (register! sym cell)
  (hash-set! %registry sym cell)
  cell)

(define (resolve sym)
  (hash-ref %registry sym #f))

(define (registered-symbols)
  (hash-map->list (lambda (k v) k) %registry))

;; ------------------------------------------------------------
;; Spaces (modules as sites)
;; ------------------------------------------------------------
(define-record-type <space>
  (make-space bindings relations)
  space?
  (bindings space-bindings)
  (relations space-relations))

(define (module->space mod)
  "Treat a Guile module as a site: objects are public bindings."
  (let ((iface (module-public-interface mod))
        (alist '()))
    (module-map
     (lambda (sym var)
       (set! alist (acons sym (variable-ref var) alist)))
     iface)
    (make-space alist '())))

(define (space->alist sp)
  `((bindings . ,(space-bindings sp))
    (relations . ,(space-relations sp))))

;; ------------------------------------------------------------
;; Dynamics (“physics”)
;; ------------------------------------------------------------
(define (set-updater! cell proc)
  (cell-updater-set! cell proc)
  cell)

(define (step! cell)
  (match (cell-updater cell)
    (#f cell)
    (proc
     (let ((new (proc cell)))
       (cell-data-set! cell new)
       cell))))

(define (tick! cells)
  (for-each step! cells)
  cells)

;; ------------------------------------------------------------
;; Demo: safe defaults so loading never errors
;; ------------------------------------------------------------
(define demo-A
  (doc!
   (register! 'A
              (make-cell
               #:data 'alpha
               #:doc "Demo cell named A. Use (resolve 'A) to fetch it."))
   "Demo binding: A cell named A."))

(define demo-B
  (doc!
   (register! 'B
              (make-cell
               #:data '(beta 1)
               #:doc "Demo cell named B."))
   "Demo binding: A cell named B."))

(relate! demo-A demo-B 'points-to)
(set-updater! demo-A (lambda (c) (cell-data c)))

;; ------------------------------------------------------------
;; EOF
;; ------------------------------------------------------------
