(use-package olivetti
    :ensure olivetti
    :after org
    :config
    (progn
      (setq olivetti-body-width 85)
      (add-hook 'org-mode-hook 'olivetti-mode)))
