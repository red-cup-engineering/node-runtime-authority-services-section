(defgroup suros nil
  "Customization variables related to the Suros personal web server.")
(defcustom
  suros-actor-public-key
  ""
  "The public key for Suros' ActivityPub actor.
Literal newlines must be replaced by \"\\n\".

See the following link for instructions on how to generate the key:
URL `https://blog.joinmastodon.org/2018/06/how-to-implement-a-basic-activitypub-server/#the-actor'"
  :group 'suros
  :type 'string)
(defcustom
  suros-base-url
  ""
  "The domain name at which your Suros will be available.
Don't include any http:// or anything after the top-level domain."
  :group 'suros
  :type 'string)
(defcustom
  suros-language-code
  "en"
  "The ISO639-1 language code that your content may be assumed
to be in."
  :group 'suros
  :type 'string)
(defcustom
  suros-actor-preferred-name
  ""
  "The name you prefer to go by in casual conversation."
  :group 'suros
  :type 'string)

(setq
 suros-config
 (ht
  ("actor-public-key"
  ("base-url"
   "suros-emsenn.pagekite.me")
  ("language-code"
   "en")
  ("preferred-name"
   "emsenn")
  ("proper-name"
   "emsenn")
  ("server-description"
   "an early-alpha personal webserver")
  ("server-name"
   "Suros")
  ("server-source-link"
   "https://emsenn.neocities.org/suros.html")
  ("username"
   "emsenn")
  ("web-port"
   9000))))
