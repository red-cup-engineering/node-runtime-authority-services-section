#lang racket

(require qtops
         "../../qualities/document.rkt")

(provide <>legal-disclosure)

(define (<>legal-disclosure t)
  (<>document
   t #:name "Legal Disclosures"
   #:content
   `(section
     (p "My legal policies aim to balance enabling my own freedom of action with the requirements placed on me by the law.")
     (p "Depending on the action, this balance may be difficult to determine. Please, assume naivety and ignorance rather than malice: explaining my harm is more likely to receive a favorable response than sending requests to participate in legal action against me without appropriate justification. I reserve the right to publish and expose all such requests made of me: they will be considered an attempt to harm me by abusing the legal system, and I will respond accordingly.")
     (p "If compelled by a Doe subpoena I may be required to disclose information about private correspondence and communication.")
     (p "I will not recognize or respect unlawful \\“gag-order\\” subpoenas from sources without the legal right to order them, and any unlawful gag-order will be considered a harmful legal request. All subpoenas specifying a “gag” which is permanent (explicitly without expiration) or indefinite (expires with further action from the issuant) are unlawful.")
     (p "I must follow the Digital Millenium Copyright Act")
     (p "If you believe I am distributing copyright-protected work without authorization, and you are the owner of the copyright or authorized to act on their behalf, you may contact me."))))
