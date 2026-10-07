(setq dam-channels
      '(("emsenn"
	 ("brutstrap-css"
	  ("name" . "Brutstrap CSS")
	  ("description" . "a cascading stylesheet for representing HTML content as it is constructed.")
	  ("creator" . "emsenn")
	  ("license" . "CC0")
	  ("versions"
	   ("current"
	    ("sourcehut"
	     ("location" . "https://git.sr.ht/~emsenn/brutstrap-css/blob/master/")
	     ("formats" . ("html" "md" "pdf" "tex" "txt")))))))))
(defun dam-get-channels
    ()
    (loop for channel
	  in dam-channels
	  collect (car channel)))
(defun dam-get-channel
    (channel)
  (cdr (assoc channel dam-channels)))
(defun dam-get-manifests
    (channel)
  "Return a list of the manifests recorded in CHANNEL."
  (loop for manifest
	in (dam-get-channel channel)
	collect (car manifest)))
(defun dam-get-manifest
    (channel id)
  "Return manifest ID from CHANNEL."
  (assoc id (dam-get-channel channel)))
(defun dam-get-versions
    (channel id)
  "Get the declared versions of ID from CHANNEL."
  (loop for versions
	in (cdr
	    (assoc "versions"
		   (dam-get-manifest channel id)))
	collect (car versions)))
(defun dam-get-version
    (channel id version)
  "Return VERSION of ID from CHANNEL."
  (cdr (assoc version (cdr (assoc "versions" (dam-get-manifest channel id))))))
(defun dam-get-sources
    (channel id version)
  "Return a list of sources for VERSION of ID."
  (loop for source
	in (dam-get-version channel id version)
	collect (car source)))
(defun dam-get-source
    (channel id version source)
  "Return SOURCE for VERSION of ID."
  (cdr (assoc source (dam-get-version channel id version))))
(defun dam-get-location
    (channel id version source)
  "Return the location for VERSION of ID at SOURCE."
  (cdr (assoc "location" (dam-get-source channel id version source)))
  )
(defun dam-get-formats
    (channel id version source)
  "Return the available formats for VERSION of ID at SOURCE from
  CHANNEL."
  (cdr (assoc "formats" (dam-get-source channel id version source))))
(defun dam-get-path
    (channel id version source format)
  "Return a url for the VERSION of ID at SOURCE from CHANNEL in FORMAT."
  (concat
   (dam-get-location channel id version source)
   id
   "."
   format))
(defun dam-open-asset
    (channel id version source format)
  "Open VERSION of ID from SOURCE from CHANNEL in FORMAT."
  (interactive "schannel: \nsid: \nsversion: \nssource: \nsformat: ")
  (browse-url
   (dam-get-path
    channel id
    version source format)))
