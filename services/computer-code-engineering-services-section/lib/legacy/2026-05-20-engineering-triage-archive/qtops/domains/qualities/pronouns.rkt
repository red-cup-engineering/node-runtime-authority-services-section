#lang racket

(provide >>make-pronoun-procedures
         >>make-e-pronoun-procedures
         >>make-she-pronoun-procedures
         >>make-they-pronoun-procedures
         >>make-he-pronoun-procedures)

(define (>>make-pronoun-procedures t
                                 #:s1 [s1 "I"]
                                 #:o1 [o1 "me"]
                                 #:dp1 [dp1 "my"]
                                 #:ip1 [ip1 "mine"]
                                 #:r1 [r1 "myself"]
                                 #:s2 [s2 "you"]
                                 #:o2 [o2 "you"]
                                 #:dp2 [dp2 "your"]
                                 #:ip2 [ip2 "yours"]
                                 #:r2 [r2 "yourself"]
                                 #:s3 [s3 "e"]
                                 #:o3 [o3 "em"]
                                 #:dp3 [dp3 "eir"]
                                 #:ip3 [ip3 "eirs"]
                                 #:r3 [r3 "eirself"])
  (list
   (cons 'pronoun-s1 (λ () s1))
   (cons 'pronoun-o1 (λ () o1))
   (cons 'pronoun-dp1 (λ () dp1))
   (cons 'pronoun-ip1 (λ () ip1))
   (cons 'pronoun-r1 (λ () r1))
   (cons 'pronoun-s2 (λ () s2))
   (cons 'pronoun-dp2 (λ () dp2))
   (cons 'pronoun-ip2 (λ () ip2))
   (cons 'pronoun-r2 (λ () r2))
   (cons 'pronoun-s3 (λ () s3))
   (cons 'pronoun-o3 (λ () o3))
   (cons 'pronoun-dp3 (λ () dp3))
   (cons 'pronoun-ip3 (λ () ip3))
   (cons 'pronoun-r3 (λ () r3))))

(define (>>make-e-pronoun-procedures t)
  (>>make-pronoun-procedures t))

(define (>>make-she-pronoun-procedures t)
  (>>make-pronoun-procedures
   t #:s3 "she" #:o3 "her" #:dp3 "her" #:ip3 "hers" #:r3 "herself"))

(define (>>make-they-pronoun-procedures t)
  (>>make-pronoun-procedures
   t #:s3 "they" #:o3 "them" #:dp3 "their" #:ip3 "theirs" #:r3 "themself"))

(define (>>make-he-pronoun-procedures t)
  (>>make-pronoun-procedures
   t #:s3 "he" #:o3 "him" #:dp3 "his" #:ip3 "his" #:r3 "himself"))
