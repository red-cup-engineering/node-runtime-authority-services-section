#lang racket

(require qtops
         "../../qualities/document.rkt")

(provide <>about-emsops)

(define (<>about-emsops t)
  (<>document
   t #:name "emsOps"
   #:content
   `(section
     (p (strong (em "emsOps")) " is a collection of "
        (a ((href "https://racket-lang.org")) "Racket")
        " declarations implemented on top of "
        (a ((href "https://github.com/emsenn/qtops/blob/master/README.md#qtops"))
           "qtOps")
        ", an interface for handling digital information as "
        (em "things") " with " (em "qualities")".")
     (p "emsOps is a collection of programming declarations - " (code "(+ 2 2)") " is a declaration that " (em "probably") " returns " (code "4") " - that create " (em "things") ", and apply " (em "qualities") " to them. Qualities give things certain capabilities: the mass quality lets you query a thing's mass, set it to something else, and increment it.")
     (p "Here's what that looks like. (Don't worry if this looks like gibberish or magic.)")
     (pre
      (code
       "(define honey (<>sweet (create-thing)))
        (honey 'sweetness)
          20
        (honey 'set-sweetness! 50)
        (honey 'sweetness)
          50"))
     (p "emsOps is a large \"stack\" of declarations like that, creating many things with many different qualities. Here's a non-comprehensive list of services and operations emsOps currently includes:"
        (ul
         (li "A simple webserver. You're probably viewing this document on that server, right now!")
         (li "A \"MUD\" server. Areas exist for the public, offering a simple role-playing game with a focus on orienting players toward decolonization, but most of the MUD is limited to authorized users and provides things like a virtualization of my real-life garden."
             (em "(If you're viewing this on the webserver, you can connect to the MUD with telnet or a MUD client through port 4242, i.e. ") (code "telnet mud.emsenn.net 4242"))
         (li "A journal. There's a journal that I can write into, either with files or (soon!) through the MUD. Some of those entries are on the " (a ((href "/logs")) "webserver.")))))))
