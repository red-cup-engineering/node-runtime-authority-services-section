(use-package pretty-mode
  :ensure pretty-mode
  :config
  (progn
    (global-pretty-mode t)
    (global-prettify-symbols-mode 1)
    (pretty-deactivate-groups
     '(:equality :ordering :order-double :ordering-triple :arrows
                 :arrows-twoheaded :punctuation :logic :sets))
    (pretty-activate-groups
     '(:sub-and-superscripts :greek :arithmetic-nary))))
