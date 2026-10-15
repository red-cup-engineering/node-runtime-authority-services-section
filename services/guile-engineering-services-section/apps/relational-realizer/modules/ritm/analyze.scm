;;; ritm/analyze.scm  ---  Relational Geometry Analyzer
;;; (c) emsenn | WTFPL or similar permissive license

(define-module (ritm analyze)
  #:use-module (ice-9 match)
  #:use-module (srfi srfi-1)
  #:use-module (ice-9 hash-table)
  #:use-module (ritm core)
  #:use-module (ritm category)
  #:use-module (ritm geometry)
  #:export (analyze-module))

;; ------------------------------------------------------------
;; Helpers
;; ------------------------------------------------------------

(define (object-count cat)
  (length (hash-map->list cons (category-objects cat))))

(define (morphism-count cat)
  (length (hash-map->list cons (category-morphisms cat))))

(define (coherence-ratio cat)
  "Rough relational density: morphisms ÷ objects²."
  (let ((objs (max 1 (object-count cat))))
    (/ (morphism-count cat) (* objs objs 1.0))))

(define (summary-line name cat)
  (format #f "~10a | ~4d objs | ~4d morphs | ρ=~5,3f"
          name (object-count cat) (morphism-count cat) (coherence-ratio cat)))

;; ------------------------------------------------------------
;; Main analysis
;; ------------------------------------------------------------

(define (analyze-module sym)
  "Perform relational geometry analysis on module SYM (a symbol list, e.g. '(web server))."
  (let* ((mod  (resolve-module sym))
         (sp   (module->space mod))
         (cat  (space->category sp))
         (shape   (category-shape cat))
         (closure (category-path-closure cat))
         (flipped (category-op cat))
         (codisc  (category-codiscrete cat)))
    (format #t "Relational Geometry Analysis of ~a\n" sym)
    (format #t "------------------------------------------------------------\n")
    (format #t "~a\n" (summary-line "Base"     cat))
    (format #t "~a\n" (summary-line "Π→ shape" shape))
    (format #t "~a\n" (summary-line "□ closure" closure))
    (format #t "~a\n" (summary-line "◇ op"      flipped))
    (format #t "~a\n" (summary-line "∇← codisc" codisc))
    (format #t "------------------------------------------------------------\n")
    (format #t "Insight:\n")
    (format #t " - Shape shows the module’s ontic grain (pure exports).\n")
    (format #t " - Closure expands latent call relations (dynamic density).\n")
    (format #t " - Opposite reveals dualities (send↔receive, input↔output).\n")
    (format #t " - Codiscrete collapses cohesion into external interface.\n")
    (format #t "------------------------------------------------------------\n")
    (values cat shape closure flipped codisc)))
