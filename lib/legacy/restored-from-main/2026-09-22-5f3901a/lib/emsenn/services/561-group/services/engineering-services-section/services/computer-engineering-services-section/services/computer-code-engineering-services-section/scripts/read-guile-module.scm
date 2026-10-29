(use-modules (ice-9 match)
             (json)
             (srfi srfi-1)
             ;; Register Guix's #~/#$ g-expression reader extensions before
             ;; reading package modules. No source form is evaluated.
             (guix gexp))

(define (read-all port)
  (let loop ((forms '()))
    (let ((form (read port)))
      (if (eof-object? form)
          (reverse forms)
          (loop (cons form forms))))))

(define (term-string value)
  (call-with-output-string
   (lambda (port) (write value port))))

(define (module-name form)
  (and (pair? form)
       (eq? (car form) 'define-module)
       (pair? (cdr form))
       (list? (cadr form))
       (term-string (cadr form))))

(define (clause-values form wanted)
  (if (and (pair? form) (eq? (car form) 'define-module))
      (let loop ((rest (cddr form)) (found '()))
        (cond
         ((null? rest) (reverse found))
         ((and (pair? rest) (eq? (car rest) wanted) (pair? (cdr rest)))
          (loop (cddr rest) (cons (cadr rest) found)))
         (else (loop (cdr rest) found))))
      '()))

(define (top-level-used-modules form)
  (if (and (pair? form) (eq? (car form) 'use-modules))
      (cdr form)
      '()))

(define forms (read-all (current-input-port)))
(define declared (filter-map module-name forms))
(define uses
  (append-map
   (lambda (form)
     (append (clause-values form #:use-module)
             (top-level-used-modules form)))
   forms))
(define exports
  (append-map
   (lambda (form)
     (append-map
      (lambda (value) (if (list? value) value (list value)))
      (append (clause-values form #:export)
              (clause-values form #:re-export))))
   forms))

(display
 (scm->json-string
  `((module . ,(if (null? declared) 'null (car declared)))
    (uses . ,(list->vector (map term-string uses)))
    (exports . ,(list->vector (map term-string exports))))))
(newline)
