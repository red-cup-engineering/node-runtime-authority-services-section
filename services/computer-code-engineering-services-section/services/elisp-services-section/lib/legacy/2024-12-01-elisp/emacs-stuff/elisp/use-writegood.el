(use-package writegood-mode
  :ensure t
  :bind (("\C-c\C-gg" . writegood-grade-level)
	 ("\C-c\C-ge" . writegood-reading-ease))
  :init
  (progn
    (writegood-mode 1))
  :config
  (progn
    (setq ispell-program-name "aspell")
    (setq ispell-list-command "--list") ;; run flyspell with aspell, not ispell
  ))
