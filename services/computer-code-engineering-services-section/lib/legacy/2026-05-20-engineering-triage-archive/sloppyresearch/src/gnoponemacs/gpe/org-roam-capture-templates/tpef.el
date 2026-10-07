("tpef" "Fediverse" plain "%?"
 :target (file+head
          (lambda ()
            (let* ((date (org-read-date nil nil nil "Post date (e.g. 2025-09-20 14:00):"))
                   (time (org-time-string-to-time date))
                   (datestr (format-time-string "%Y%m%d%H%M%S%z" time))
                   (orgdate (format-time-string "<%Y-%m-%d %a>" time)))
              (cons (format "post-to-emsenn-kolektiva-social-%s.org" datestr)
                    (format "#+title: Post to @emsenn@kolektiva.social, %s\n#+date: %s\n#+author: emsenn\n\n"
                            orgdate orgdate)))))
 :unnarrowed t
 :form "[[id:a299fe51-7629-4b6e-afa0-7c7717371cc7]]")
