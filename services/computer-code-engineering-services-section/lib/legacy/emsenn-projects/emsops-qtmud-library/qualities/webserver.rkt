#lang racket

(require web-server/servlet
         web-server/servlet-env
         web-server/http/request-structs
         qtops/qualities/animation
         "library.rkt")

(provide <>webserver
         >>make-webserver-procedures)

(define ((>render-css t))
  "body {
     position: relative;
     background-color: #ddc;
     color: #413;
     font-family: serif;
     margin: 0 auto;
     padding-bottom: 6rem;
     min-height: 100%;
     font-size: 0.8em;
     font-family: sans-serif;
   }
   article {
     background-color: #eed;
     box-shadow: 0 1px 3px rgba(0,0,0,0.12), 0 1px 2px rgba(0,0,0,0.24);
     width: 75vw;
     max-width: 45em;
     margin: 0.5em auto;
     padding: 1em;
   }
   header {
   margin-bottom: 2em;
   padding-bottom: 0.5em;
   border-bottom: 0.2em dotted #444;
   }
   h1, .title { margin: 0.2em 0 0.2em 0; font-size: 3.2em; }
   h1 small { font-size: 0.5em; margin: 0 0.2em 0 0.2em; padding: 0.2em;}
   main, #content {
   width: 75vw;
   max-width: 40em;
   margin: 0 auto;
   line-height: 1.6;
   margin-bottom: 3rem;
   }
   img { width: 30em; max-height: 80vh; }
   footer, #postamble {
   width: 75vw;
   max-width: 45em;
   margin: 0 auto;
   overflow: hidden;
   margin-top: 2em;
   padding-top: 0.5em;
   border-top: 0.1em dotted #444;
   }
   section {
   margin-bottom: 0.5em;
   padding-bottom: 0.5em;
   }
   .outline-3 {
   border-bottom: 0.1rem dotted #444;
   }
   #recent-logs, #recent-bulletins {
     box-shadow: 0 1px 3px rgba(88,88,00,0.12), 0 1px 2px rgba(44,11,33,0.24);
   }
   .pages-listing {
     padding: 0.5em 2em;
   }
   .pages-listing ul { list-style-type: none; width: 100%; padding: 0; margin 0 auto; }
   .pages-listing li {
     border-bottom: 0.1em dashed #413;
     padding-bottom: 0.2em;
   }
   .page-brief .page-summary {
     font-size: 0.7em;
   }
   .page-brief .page-keywords { font-size 0.8em; }
   blockquote {
   padding: 0.5rem;
   border-left: 0.1em solid #444;
   }
   table {
   border-collapse: collapse;
   border-spacing: 0;
   empty-cells: show;
   border: 0.1em solid #444;
   }
   thead { font-family: sans-serif; }
   th, td {
   padding: 0 0.3em;
   border: 0.01em solid #444;
   }
   img {
   max-width: 80vw;
   vertical-align: middle;
   }
   pre, .src {
   padding: 0.5em;
   border: 0.1em solid #444;
   white-space: pre-wrap;
   overflow-x: scroll;
   text-overflow: clip;
   }
   dt {
   font-weight: normal;
   display: inline-block;
   border-bottom: 0.1rem dotted #444;
   }
   #text-index dt { border-bottom: none; }
   h2, h3, h4, h5, h6, h7, h8, h9, h10 {
   display: block;
   font-family: sans-serif;
   margin: 0.2em auto 0.5em 0;
   }
   h2 { text-align: left; font-size: 2em;}
   h3 {
   font-size: 1.8em;
   }
   h4 {
   font-size: 1.6em;
   }
   h5 {
   font-size: 1.4em;
   margin: 0.5em 0 0.2em 10%;
   }
   h6 {
   font-size: 1.2em;
   margin: 0.5em 0 0.2em 30%;
   }
   a {
   text-decoration: none;
   color: #880;
   display: inline;
   position: relative;
   border-bottom: 0.1rem dotted;
   line-height: 1.2;
   transition: border 0.3s;
   }
   a:hover {
   color: #aa2;
   outline-style: none;
   border-bottom: 0.1rem solid;
   }
   a:visited { color: #934; }
   a:visited:hover { color: #b56; }
   a:focus {
   outline-style: none;
   border-bottom: 0.1rem solid;
   }
   ::selection { background-color: #777; color: #eee; }
   a::selection { background-color: #ccc; }
   .org-todo {
   background-color: #ddd;
   color: #333;
  font-size: .8rem;
  float: right;
  }
  .org-src-container + .example {
  margin-left: 8em;
  }
  label.org-src-name {
  margin: 0 0 0 3em;
  font-family: sans-serif;
  font-size: 1rem;
  line-height: 0;
  }
  .skip-to-content {
  opacity: 0;
  position: absolute;
  }
  .skip-to-content:focus{
  opacity:1
  }
  ul { max-width: 85%; }
 ")

(define ((>render-html:document t) d)
  ((t 'procedure 'render-html:page)
   #:title (d 'name)
   #:content (d 'content)))

(define ((>render-html:page t)
         #:title [title #f]
         #:content [content #f]
         #:description [description #f])
  `(html ((xmlns "http://www.w3.org/1999/xhml")
          (xml:lang "en")
          (lang "en"))
         (head (title ,(if title title (t 'name)))
               (style ,(t 'render-css)))
         (body
          (a ((class "skip-to-content")
              (href "#content"))
             "Skip to page content")
          (article
           (header
            (h1 ,(if title title (t 'name)))
            ,(if description `(p ,description) `(p "")))
           ,(if content
                `(main
                  (section ((id "content"))
                           ,content))
                "")))))

(define ((>xexpr-servlet t) r x)
  (response/xexpr x))

(define ((>document-servlet t) req doc-name)
  ((t 'procedure 'xexpr-servlet)
   req
   (if (t 'has-document? (string->symbol doc-name))
       ((t 'procedure 'render-html:document)
        (t 'document (string->symbol doc-name)))
       ((t 'procedure 'render-html:page)
        #:content "No matching document found."))))

(define ((>homepage-servlet t) req)
  ((t 'procedure 'xexpr-servlet)
   req
   ((t 'procedure 'render-html:page)
    #:content
    `(section
      (p "This is my personal webserver. It's running on software I wrote myself, so please excuse any issues. "
         (a ((href "docs/about-emsops"))
            (em "(Learn more here.)")))
      (nav ((id "site-overview"))
           (ul
            (li
             (a ((href "/docs/contact"))
                "contact me"))
            (li
             (a ((href "/docs/support"))
                "support me"))
            #;(li
               (a ((href "/stories/"))
                  "my stories"))
            #;(li
               (a ((href "/projects/"))
                  "my projects"))))))))

(define ((>404-servlet t) req)
  (response/xexpr
   ((t 'procedure 'render-html:page)
    #:content "The resource you've requested doesn't exist.")))

(define ((>thing-servlet t) req thing-name)
  (define R
    ((λ () (define r "")
        (λ ([l #f]) (if l (set! r (string-append r l)) r)))))
  (define matching-things
    (filter procedure?
            (map (λ (q) (when (q 'name=? thing-name) q))
                 ((t 'universe) 'things))))
  (cond
    [(null? matching-things)
     (R "No matching things!")]
    [(= 1 (length matching-things))
     (define w (first matching-things))
     (R (w 'name))
     (when (w 'has-procedure? 'description)
       (R (w 'description)))]
    [(> (length matching-things) 1)
     (R (format "More than one match: ~a"
                (map
                 (λ (t) (t 'name))
                 matching-things)))])
  (response/xexpr
   `(html (head (body ,(R))))))

(define ((>main-servlet t)) (void))

(define ((>start-main-servlet! t))
  (define servlet
    (thread
     (λ ()
       (serve/servlet (t 'procedure 'http-request-handler)
                      #:listen-ip #f
                      #:port 8000
                      #:servlet-regexp #rx""
                      #:launch-browser? #f
                      #:extra-files-paths
                      (list
                       (build-path (current-directory)))))))
  (t 'remove-animation! 'start-main-servlet!)
  (t 'set-procedure! 'main-servlet (λ () servlet)))

(define ((>suspend-main-servlet t))
  (thread-suspend (t 'main-servelet)))

(define ((>http-request-handler t) r)
  (define-values (dispatch generate-url)
    (dispatch-rules
     [("") (t 'procedure 'homepage-servlet)]
     [("docs" (string-arg)) (t 'procedure 'document-servlet)]
     [("logs") (t 'procedure 'log-listing-servlet)]
     [("logs" (string-arg)) (t 'procedure 'log-servlet)]
     [("things" (string-arg)) (t 'procedure 'thing-servlet)]
     [else (t 'procedure '404-servlet)]))
  (dispatch r))

(define (>>make-webserver-procedures t)
  (list
   (cons 'render-css (>render-css t))
   (cons 'render-html:page (>render-html:page t))
   (cons 'render-html:document (>render-html:document t))
   (cons 'xexpr-servlet (>xexpr-servlet t))
   (cons 'document-servlet (>document-servlet t))
   (cons 'homepage-servlet (>homepage-servlet t))
   (cons '404-servlet (>404-servlet t))
   (cons 'thing-servlet (>thing-servlet t))
   (cons 'http-request-handler (>http-request-handler t))
   (cons 'main-servlet (>main-servlet t))
   (cons 'start-main-servlet! (>start-main-servlet! t))
   (cons 'suspend-main-servlet (>suspend-main-servlet t))))

(define (<>webserver t
                     #:name [name #f]
                     #:documents [documents #f])
  (unless (t 'has-procedure? 'animations)
    (t 'set-procedures! (>>make-animation-procedures t)))
  (unless (t 'has-procedure? 'documents)
    (t 'set-procedures! (>>make-library-procedures t)))
  (t 'set-procedures! (>>make-webserver-procedures t))
  (when name (t 'set-name! name))
  (when documents (t 'fill-documents! documents))
  (t 'add-animation! (list 'start-main-servlet! 1 100))
  t)
