:PROPERTIES:
:ID:       de595b66-d89d-41d6-87fc-724482ec16ec
:form:     [[id:fc06db27-d77d-4ca1-b801-54e6edc7c157][artist]]
:public:   true
:END:
#+title: music artist
#+date: 2025-07-21
#+author: emsenn
#+index: artist!music artist
#+index: music!music artist


#+begin_src elisp :results value raw :exports results :eval yes
  (let* ((nodes
          (org-roam-db-query
           [:select [*]
            :from nodes
            :where (and
                    (like properties '"%form%music artist%")
                    (like properties '"%public%true%"))]))
         (sorted-nodes
          (sort nodes
                (lambda (a b)
                  (string-lessp (nth 8 a) (nth 8 b))))))
    (mapconcat
     (lambda (node)
       (format "- [[id:%s][%s]]" (car node) (nth 8 node)))
     sorted-nodes
     "\n"))
#+end_src

#+RESULTS:
- [[id:ae0cb5fc-165a-44ff-8979-95c263f2e87b][King Gizzard & The Lizard Wizard]]
- [[id:d8e776b1-21e8-45fb-aee7-6b4f44d28823][Parts & Spares]]
- [[id:b48584c1-8bd6-4cc8-acf8-655c9285e3e6][von Stuck]]
