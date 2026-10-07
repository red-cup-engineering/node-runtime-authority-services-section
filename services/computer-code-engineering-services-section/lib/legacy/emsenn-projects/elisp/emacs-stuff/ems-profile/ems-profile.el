;;; ems-profile.el --- emsenn's package for handling project metadata

;; Copyright (C) 2019 emsenn

;; Author: emsenn <emsenn@emsenn.net>
;; URL: http://github.com/emsenn/ems-profile.el/
;; Version: 0.1.0
;; Package-Requires: ((emacs "26.1"))
;; Keywords: emsenn

;; This file is not part of GNU Emacs.

;;; Commentary:

;; This is my package for tracking some metadata about my
;; personal projects, and while it it is licensed for the good
;; of the commons, it probably shouldn't be used by anyone who
;; isn't me.


;;;; Installation

;;;;; Manual

;; Put this file in your load-path, and put this in your init
;; file:

;; (require 'ems-profile)

;;;; Usage

;;;; Tips

;;;; Credits

;;;; Future Plans

;;; License:


;;; Code:

;;;; Requirements
;
;;; Customization

(defgroup ems-profile nil
  "Settings for `ems-profile'."
  :link '(url-link "http://gitlab.com/emsenn/ems-profile.el"))

(defcustom ems-profile-preferred-name "emsenn"
  "Your preferred name, such as your given name or a common nickname."
  :type 'string)
(defcustom ems-profile-given-name "Morgan"
  "Your given name."
  :type 'string)
;;;; Functions
;;;;; Commands
;;;; Footer

(provide 'ems-profile)

;;; ems-profile.el ends here
