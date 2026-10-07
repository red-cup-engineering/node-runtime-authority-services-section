#lang racket

(require qtops
         "../../qualities/document.rkt")

(provide <>support)

(define (<>support t)
  (<>document
   t #:name "Support emsenn"
   #:content
   `(section
                (p "I focus my life around personal decolonization and helping those in my community do the same, with a focus on dismantling food apartheid.")
                (p "This is made possible with contributions from people like you.")
                (p (strong (em "Thank you!")))
                (ul
                 (li "Donate money"
                     (ul
                      (li "One-time:"
                          (ul
                           (li (a ((href "https://paypal.me/emsenn"))
                                  "PayPal"))
                           (li (a ((href "https://ko-fi.com/emsenn"))
                                  "Ko-fi"))))
                      (li
                       "Recurring:"
                       (ul
                        (li
                         (a
                          ((href
                            "https://liberapay.com/emsenn/donate"))
                          "LiberaPay"))
                        (li (a ((href "https://patreon.com/emsenn"))
                               "Patreon"))))))
                 (li "Donate Supplies"
                     (ul
                      (li
                       "Please "
                       (a ((href "/contact.html")) "contact me")
                       " to receive an up-to-date shipping address.")
                      (li "(Or if you're around Chapel Hill, NC, to coordinate in-person drop-off or pick-up.)")
                      (li "What follows is an incomplete list of currently desired supplies, but other items are accepted, again, just reach out.")
                      (li "large tupperware bins")
                      (li "wooden cutting boards")
                      (li "2 liter soda bottles (for gardening)")
                      (li "tubes from empty toilet paper rolls (also for gardening)")
                      (li "planting trays, planting plots (pretty much anything for gardening")
                      (li "plastic drawers")))))))
