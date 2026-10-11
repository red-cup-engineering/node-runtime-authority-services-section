(defadvice load-theme (before theme-dont-propagate activate)
  (mapc #'disable-theme custom-enabled-themes))
