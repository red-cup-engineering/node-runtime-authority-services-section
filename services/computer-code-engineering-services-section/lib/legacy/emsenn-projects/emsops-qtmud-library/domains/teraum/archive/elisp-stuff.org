#+TITLE: Teraum
#+author: emsenn
#+EXPORT_FILE_NAME: teraum
#+HUGO_BASE_DIR: ~/src/personal-website
#+HUGO_SECTION: .
#+TOC: headlines 2
* Introduction
*/Teraum/* is a tragically funny fantasy world.

{{{document-eli(default)}}}
* Data
  :PROPERTIES:
  :header-args: :tangle ./elisp/teraum-data.el
  :END:
#+begin_src elisp
  (setq teraum-data '())
#+end_src
** People
*** Anadini, Jenos
#+begin_src elisp
  (push
   '(anadini-jenos
     (name . "Jenos Anadini")
     (description . "Jenos Anadini is a middle-aged human man who works for Honeyfern Laboratory as an archivist.")
     (inventory
      (easy-smoking-pipe .)))
   teraum-data)
#+end_src
** Places
*** DRAFT Gloaming
#+begin_src elisp
#+end_src
*** Belcaer
#+begin_src elisp
(push '(belcaer
(name . "Belcaer")
(description . "Belcaer...")
(location . gloaming))
teraum-data)
#+end_src
*** Caliper Street
#+begin_src elisp
  (push
   '(caliper-street
     (name . "Caliper Street")
     (description . "Caliper Street runs through the Brass Ward, in Ack.")
     (nav
      (114 . twisted-alembic)))
   teraum-data)
#+end_src
*** Twisted Alembic
#+begin_src elisp
  (push
   '(twisted-alembic
     (name . "Twisted Alembic")
     (description . "The Twisted Alembic is one of the oldest pubs in the city of Ack. It has a reputation for being where the city's more eccentric engineers and chemics spend time.")
     (nav
      (south-door . caliper-street)))
   teraum-data)
#+end_src
*** Green Delta
#+begin_src elisp
  (push
   '(green-delta
     (name . "Green Delta")
     (description . "The Green Delta is a fertile region, dense with farms and small villages.")
     (nav
      (east . central-plains)
      (southeast . gloaming)
      (south . widewoods)
      (west . optic-ocean)))
   teraum-data)
#+end_src
** Things
*** pipe, easy-smoking
#+begin_src elisp
  (push
   '(pipe-easy-smoking
     (name . "easy-smoking pipe")
     (description . "The easy-smoking pipe is a wooden pipe which emits an intoxicating smoke. The magic comes from the pipe itself; anything burnt in it produces the same effect.")
     (location . anadini-jenos))
   teraum-data)
#+end_src
** Species
*** humans
#+begin_src elisp
  (push
   '(humans
     (name . "humans")
     (description . "Humans are a sapient but mundane species of upright ape."))
   teraum-data)
#+end_src
* Timeline
  :PROPERTIES:
  :header-args: :tangle ./elisp/teraum-timeline.el
  :END:
#+begin_src elisp
(setq teraum-timeline '())
#+end_src
** Prehistory
#+begin_src elisp
(push
((concat
(teraum-read-name 'gods) " from around the multiverse create the " (teraum-read-name 'worldkeep) " and then buid teraum around it.") . (50000bc))
teraum-timeline)
#+end_src
** The Great Wars
*** 43pc
**** Summer, 43pc
***** 21st of Summer, 43pc
#+begin_src elisp
  (push
   '(43pc (Summer (21
   (concat
    "In " (teraum-read-name 'pled) ", "
    (teraum-read-name 'anadini-jenos)
    " is born."))))
   teraum-timeline)
#+end_src

* Functions
  :PROPERTIES:
  :header-args: :tangle ./elisp/teraum-functions.el
  :END:
** Read Records
*** Read Record
#+begin_src elisp
  (defun teraum-read-record
      (subject)
    "Returns the list representing the record of SUBJECT."
    (cdr (assoc subject teraum-data)))
#+end_src
*** Read Name
#+begin_src elisp
  (defun teraum-read-name
      (subject)
    "Returns the name of the SUBJECT."
    (cdr (assoc 'name (teraum-read-record subject))))
#+end_src
*** Read Desc(ription)
#+begin_src elisp
  (defun teraum-read-desc
      (subject)
    "Returns the description of the SUBJECT."
    (cdr (assoc 'description (teraum-read-record subject))))
#+end_src
*** Read Nav(igation)
#+begin_src elisp
  (defun teraum-read-nav
      (subject)
    "Returns the nav items of the SUBJECT."
    (cdr (assoc 'nav (teraum-read-record subject))))
#+end_src
*** Read Nav(igation) Item
#+begin_src elisp
  (defun teraum-read-nav-item
      (subject item)
    "Returns the record of the ITEM in the SUBJECT's navigation list."
    (cdr (assoc item (teraum-read-nav subject))))
#+end_src
*** Read Location
#+begin_src elisp
  (defun teraum-read-location
      (subject)
    "Returns the location of SUBJECT."
    (cdr (assoc 'location (teraum-read-record subject))))
#+end_src
** Make Records
** Build Results
* Reference Books
** DRAFT Arathel Gazetteer
*** Introduction
*** Overview
*/Arathel/* is the /human/-populated county seat of /Arathel County/,
in the northwest /Green Delta/. First settled in 478bc as a logging
community, Arathel is one of the larger towns in the community. It is
governed by a council of local commercial leaders. its primary exports
are /wool/, /limestone/, and /cokeberries/. Notably, Arathel was the capital
of the /Astar Empire/.
*** History
**** Founding of Arathel
    :PROPERTIES:
    :CUSTOM_ID: founding
    :END:
#+INDEX: 478bc!"Founding of Arathel" in /Arathel Gazetteer/
#+INDEX: 477bc!"Founding of Arathel" in /Arathel Gazetteer/
#+INDEX: 474bc!"Founding of Arathel" in /Arathel Gazetteer/
#+INDEX: 470bc!"Founding of Arathel" in /Arathel Gazetteer/
The town of Arathel was first settled by humans in 478bc, on a hill
south of the /Kaiper River/. The town first grew around the /Reinhard
Lumber Mill/, built in 477bc by /Osmits Reinhard/. Its prosperity was
aided by trade with the fisherfolk of /Ack/, who always needed fresh
lumber for their ships.

In 474bc, the community built a church in honor of /Povator/, a god of
woodlands.

In 470bc, /Osmits Reinhard/ built a small estate northwest of town,
closer to the /Kaiper River/, and began taxing the residents in
exchange for maintaining a small armory and militia.
**** Early Growth of Arathel
    :PROPERTIES:
    :CUSTOM_ID: early-growth
    :END:
From 470bc until 460bc the town continued to grow at a reasonable
pace. /Osmits Reinhard/ constructed a watchtower on the road southwest
out of town, toward /Ack/, while the road southeast toward /Pled/
became dotted with /wheat/ farms. The town began to export the local
/limestone/ to /Ack/, who was using it construct the many estates its
growing noble class required, and /wool/ to /Pled/. In 464bc, the
church to /Povator/ was expanded, and in 462bc, /Osmits Reinhard/
commissioned the planting of what became known as the /Borderwood/, a
strip of pine forest which separated Arathel from the countryland to
the southwest, between it and /Ack/.

As Arathel grew in size it became more of a target for bandits in the
area, which pushed /Osmits Reinhard/ to grow the size of the local
militia, drawing on the labor force of his lumber mill.
**** Arathel's First Recession
    :PROPERTIES:
    :CUSTOM_ID: first-recession
    :END:
The expense of the militia, and reduced workforce at his mills, caused
/Osmits Reinhard/ to fall behind in paying wages to his men, and in
the summer of 460bc, he was hanged in the town square. Control of his
mill - and subsequently the town - fell to a self-appointed council
consisting of local tradesfolk. The tradesfolk immediately
commissioned the construction of new wells and agreed that a sizeable
portion of the late /Osmits Reinhard/'s seized assets should be used
to again expand the /Povator Church/.

Unfortunately the expenses left Arathel unable to maintain a militia,
and bandits moved into the countryside, suppressing trade between the
town and /Pled/. The town council attempted to negotiate a tribute to
the bandits, but were attacked and fled the region.

Absent a government - who also were many of their skilled craftsmen -
the town fell into a deep recession. The region was fertile farmland,
so population continued to grow, but the town's trade with /Ack/ and
/Pled/ slowed to a trickle.
**** Arathel and the Founding of the Astar Empire
    :PROPERTIES:
    :CUSTOM_ID: founding-of-the-astar-empire
    :END:
Without trade routes to raid, many of the local bandits settled down
near the road to /Pled/, which extended southeast out of Arathel. Some
formed a little suburb past the town's /wheat/ farms and in 454bc they
built a small church to one of their gods, /Siggrit/, of /earthworms/.

In 442bc, /Povator/'s worshippers in the area constructed a
significantly nicer church on the crest of a hill north of town,
overlooking the /Kaiper River/, and several families in the area began
to construct large elegant estates. These works encouraged local
industry and again, trade with the neighboring communities of /Ack/ and
/Pled/.

As the population grew and industry began to revitalize, a reformed
gentry grew in the town. A notable member of this gentry was /Henri
Astar/, who by 440bc owned many of the farms that had been built in
Arathel and the area around it. In 438bc, /Henri/ used his wealth to
organize a militia which attacked the humans living south of the /Green
River/, in the /Indenon Empire/.

The attack quickly escalated into a continued war, which encouraged
local industry and formalized Arathel as the capital of the new /Astar
Empire./
*** Areas
**** Old Arathel
    :PROPERTIES:
    :CUSTOM_ID: old-arathel
    :END:
***** First Church of Povator
     :PROPERTIES:
     :CUSTOM_ID: irst-church-of-povator
     :END:
First constructed in 474bc, the */First Church of Povator/* is a
historical church in /Old Arathel/, originally serving as a place to
worship /Povator/, a god of woodlands.
***** Reinhard Estate
     :PROPERTIES:
     :CUSTOM_ID: reinhard-estate
     :END:
***** Reinhard Lumber Mill
     :PROPERTIES:
     :CUSTOM_ID: reinhard-lumber-mill
     :END:
The */Reinhard Lumber Mill/* is a lumber mill in the town of
Arathel first opened in 474bc.

***** Second Church of Povator
     :PROPERTIES:
     :CUSTOM_ID: second-church-of-povator
     :END:
***** Siggrit Temple
     :PROPERTIES:
     :CUSTOM_ID: siggrit-temple
     :END:

* Adventures
** The Crown of Idbol Bark
   :PROPERTIES:
   :adventure-inwhich: the party attempts to arrest an upstart "king"
   :adventure-length: two to four hours
   :adventure-question: Who is "King Bark," really?
   :adventure-year: 80pc
   :END:
#+macro: bow-adventure-brief */{{{title}}}/* is a /tabletop role-playing *{{{doc}}}*/ in which {{{property(adventure-inwhich)}}}, usually taking {{{property(adventure-length)}}} to complete.
#+macro: bow-adventure-is-written-for-bow This {{{doc}}} was written to be played with the /Brave Old World/ ruleset, but can be adapted for any system.
#+macro: bow-adventure-is-in-playtesting This {{{doc}}} is ready to be used, but it isn't finished. Things might be unfair to players, or unclear for narrators.
{{{bow-adventure-brief}}}

{{{bow-adventure-is-written-for-bow}}}

{{{bow-adventure-is-in-playtesting}}}

#+ATTR_LATEX: :width .3\textwidth :thickness 0.8pt
-----

Danger is never far in the /Gloaming/, where marshes and mesas give home to bandits and beasts. The lone /trade road/ through the region is a gauntlet for traveling merchants.

The town of /Belcaer/ is a haven for those travelers. The same /magic/-users who built the /trade road/ built the town as a fortress. On top of a limestone mesa, the town now exists to serve travelers. Residents offer meager services, hoping to win the travelers' coin.

Recently there haven't been many coins to take. A bandit calling himself "King Brag" has been mugging travelers. Now, farmers are reporting missing livestock.

A local official named /Abeth Harbrook/ believes she has found where the "king" is hiding: /Jacob's Folly/, an tower built and abandoned in the forgotten past.

She's offering to pay anyone who captures the "king," and the party has gathered at her office.

*/{{bow-adventure-question}}}/*

{{adventure-era(Reconstruction Era)}}}
{{teraum-define(reconstruction-era)}}}

{{adventure-has-character-templates}}}

To the extent possible under U.S. law, the author of this work has
waived all copyright and related or neighboring rights to this work.


{{teraum-readmore}}}

#+ATTR_LATEX: :width .3\textwidth :thickness 0.8pt
-----

Before beginning the session, your party should know:
- How much does each of them weigh, with and without equipment?
- Is anyone a high-ranking officer in the /Chandlers Guild/?

{{project-latex-logomark}}}
{{project-latex-licensemark}}}

#+LATEX: \newpage

{{adventure-narrator-warning}}}
*** DRAFT Exposition
  :PROPERTIES:
  :CUSTOM_ID: exposition
  :END:
**** DRAFT Settings
   :PROPERTIES:
   :CUSTOM_ID: settings
   :END:
- */Belcaer:/* A town of about four-hundred, built of stone atop a
  mesa, overlooking the only major road in the /Gloaming/.
- */The Gloaming:/* A region of fens and marshes, broken up by mesas
  and rock outcroppings. The region is unsettled and lawless.
- */Jacob's Folly:/* A three-storey limestone tower built about eight
  miles west of /Belcaer/, far from any road or notable landmark.
**** DRAFT Cast
   :PROPERTIES:
   :CUSTOM_ID: cast
   :END:
- */Abeth Harbrook:/* The local /Chandlers Guild/ representative.
- */King Idbol Bark:/* A /goblin/ who lives with his clan in /Jacob's
  Folly/.
*** DRAFT The Plot
  :PROPERTIES:
  :CUSTOM_ID: the-plot
  :END:
**** DRAFT Scene One: Receiving the Quest
   :PROPERTIES:
   :CUSTOM_ID: scene-one
   :END:
#+INDEX: Belcaer!"Scene One" in /The Crown of Idbol Bark/
#+INDEX: Harbrook, Abeth!"Scene One" in /The Crown of Idbol Bark/
The members of the party are to meet, together or individually, with
/Abeth Harbrook/, at her offices in the /Guildhouse/. She is the
highest-ranked local official of the /Chandlers Guild/, a commercial
organization based in the distant city of /Ack/.

They rely on trade coming through the /Gloaming/, so have recently
invested in the region and the town. Much of the /trade road/ has been
recently covered in gravel. In town, they built the /Guildhouse/, a
massive pine structure that sticks out over the edge of the mesa, held
up by a lattice of timber.

/Abeth Harbrook/ has kept the party waiting, and now comes out to meet
them in the waiting room. She apologies for addressing them as a
group, if they aren't already associated.

Two seasons ago, /Abeth Harbrook/ first heard rumors of a "king," from
travelers that claimed they were mugged on the /trade road/. At first
she dismissed the claims as exaggerations. She thought they wanted to
get out of paying guild tariffs.

Last season, livestock began to disappear from local farms. Barns and
silos were painted to say "/King Bark/ Was Here" and "/Idbol Bark/ Is
King."

Recent attempts to arrest the "king" failed, but revealed the location
of his hideout: /Jacob's Folly/, a short tower built eight miles
outside of town.

*/How does the party plan to capture/ King Idbol Bark?*

If the party *risks* interrogating /Abeth Harbrook/, she may include
that victims claimed the bandits were exceptionally tall and wore
masks. She withheld this information because she thought it was an
exaggeration.

An adventurer *knowledgable* about /goblin/ culture may recognize
/"Bark"/ as a /goblin/ surname.
**** DRAFT Scene Two: Travel to the Tower
   :PROPERTIES:
   :CUSTOM_ID: scene-two
   :END:
#+INDEX: Gloaming!"Scene Two" in /The Crown of Idbol Bark/
/Jacob's Folly/ is approximately eight miles from /Belcaer/. Six of
those miles are northwest along the /trade road/, The final two
are through shallow marsh, broken by massive limestone outcroppings.

*/How does the party get to Jacob's Folly?/*

If traveling at night or in inclement weather, the party *risks*
getting lost, though *knowledge* of navigation would help.

If the party travels quietly (such as at night or in inclement
weather,) as they approach the tower, they will remain undetected
until reaching "Scene Three."

Otherwise, they will be met by a group of "bandits" on the road, who
declare, in sqeaky rough voices, that declares they are in the
territory of /King Bark/, and must surrender their money and supplies.

Each bandit is actually two /goblins/ in a long cloak, one standing on
the others shoulders and wearing a mask.

*/How does the party handle these "bandits"?/*

If the party has horses or other livestock, the goblins will attempt
to steal these even if the party refuses to surrender. Otherwise, they
are more inclined to run than fight. If captured, they will happily
give the party directions to /Jacob's Folly/, saying that /King Bark/
would be happy for them to come bend the knee.
**** DRAFT Scene Three: The Tower Exterior
   :PROPERTIES:
   :CUSTOM_ID: scene-three
   :END:
#+INDEX: Jacob's Folly!"Scene Three" in /The Crown of Idbol Bark/
The limestone outcroppings in the marsh hide /Jacob's Folly/ until the
party is nearly there.

The limestone tower is three-storeys, and approximately twenty-five
feet tall and ten feet across. It is in a clearing about fifty yards
across. The tower's entrance has been sealed with the same limestone
bricks as the tower. There are a couple of windows near the top. Pine
planks, five on each side, are shoved into the mortar. They form an
unstable ladder up to the windows.

/Goblins/ are working around the tower, tearing grass out of the muck
and stuffing it into sacks. There is a burnt-out bonfire with horse
bones in it.

*/How does the party get into Jacob's Folly?/*

When a member of the party moves into the clearin,g any goblins near
them will quietly move toward the tower, informing others on the way.

Some goblins will remain outside the tower, hiding behind rock
outcroppings in the field and throwing stones and debris at the party.
If the party *risks* engaging with any of those /goblins/, goblins at
the top of the tower will have time to start burning straw on the roof
the tower, which they will drop on the party when they approach the
bottom of the tower.

If approaching in the evening, the party *risks* being noticed by an
owlbear mother that nests on the top of the tower, who will swoop down
and harass them, making the /goblins/ aware of them. The /owlbear
mother/ will attempt to carry any small (<120lb) adventurer into its
nest, where two hungry /owlbear hatchlings/ are waiting for them.


Placing more than 120lb on any single rung of the goblins' improvised
ladder is *risk*, with every 20lb making it *riskier*. Depending on
the result, a rung could loosen or break. The adventurer might gain a
fear of heights, or could fall, and even break a bone.

An adventurer who gets to the roof of /Jacob's Folly/ would be able
to take those /hatchlings/ and raise them, but unless the /mother/ is
killed, she will follow her hatchlings to the ends of the world and
try and get them back.
**** DRAFT Scene Four: The Tower Interior
   :PROPERTIES:
   :CUSTOM_ID: scene-four
   :END:
#+INDEX: Jacob's Folly!"Scene Four" in /The Crown of Idbol Bark/
The inside of the tower is dark, stinky, and beginning to fill with
acrid smoke.

When the party enters the room at the top of the tower, through the
window on the third storey, they'll find an empty room with some
sticks, dry piles of dung, buckets, and a large brass dish that's
clearly been used for fires, and might still have straw burning in it.
The goblins will retreat down underneath the trap door on the ground
floor.

There are two other "floors" inside the tower, though they are empty
except for more dirty straw and dung. There is a large, heavy wood
door in the floor at the ground level.


Once the party has entered the tower, all the goblins are underneath
this trap door, and have removed the ladder normally placed under it.
To get to the floor below is a seven-foot drop.

Smoke rises through the trapdoor, filling the tower with thicker
smoke that makes every risk riskier.

If the party is on the ground floor during the daytime, they will see
light entering the room through cracks in the filled-in doorway. A
*strong* character might *risk* knocking the mortar down, letting the
smoke out of the tower.

Opening the trapdoor exposes the party to further harassment from the
goblins, but provides an opportunity for dialog. The goblins will
call the party cowards, and say that if they come down there, /King
Bark/ is going to get them.

*/How does the party get to/ King Bark?*
**** DRAFT Scene Five: The Tower Basement
   :PROPERTIES:
   :CUSTOM_ID: scene-five
   :END:
#+INDEX: Jacob's Folly!"Scene Five" in /The Crown of Idbol Bark/
#+INDEX: Bark, Idbol!"Scene Five" in /The Crown of Idbol Bark/
#+INDEX: Crown of Idbol Bark!"Scene Five" in /The Crown of Idbol Bark/
The room is circular, a bit wider in diameter than the tower above,
and is full of farm tools and preserved foodstuff and grains.

Among the approximately two-dozen goblins in this room is one wearing
a "crown" made of twisted-together silverware: /Idbol Bark/, leader of
this group of goblins.

*/How does the party capture King Bark?/*

The goblins have no further means of retreat, so will fight until
unable. King Bark has no exceptional combat skills, and no goblin is
armed with anything more than farm and kitchen tools.
*** DRAFT Epilogue
  :PROPERTIES:
  :CUSTOM_ID: epilogue
  :END:
#+INDEX: Harbrook, Abeth!"Epilogue" in /The Crown of Idbol Bark/
#+INDEX: Crown of Idbol Bark!"Epilogue" in /The Crown of Idbol Bark/
Once /King Bark/ and his goblins have been captured, disbanded, or
eliminated, the party should return to /Belcaer/ and tell /Abeth
Harbrook/ what happened, and potentially turn over custody of King
Bark and other goblins to her custody.

- How will /Abeth Harbrook/ react to claims or evidence of /goblins/?
- Who has possession of the /Crown of Idbol Bark/? Each utensil in it
  was magic in some way, though they're inactive now. To the right
  person, or in the right future, it might be quite valuable.
* Essays
** What Is Teraum?
      :PROPERTIES:
      :CUSTOM_ID: what-is-teraum
      :END:
At its heart, Teraum is a fiction. It's been a part of my life since I was a young child: it was the place where adventures were set. It was always kind of a silly place, with wizards who liked to play pranks, and knights who fell in the mud when trying to mount their horses.

As I grew, so did the place where adventures were set. I wrote stories set there: short, long, funny, mysterious, scary stories. The fiction became more concrete. Cities gained names, empires were assigned histories, and heroes learned about themselves.

The world itself gained a name, Tero kun thaum. Butchered Esperanto and freshly vulgarized Latin, the name means "Earth with magic." Eventually it was shorted to "Teraum."

Much of what was concrete about Teraum was lost in the chaos of early adulthood, but in recent years I've had an interest in coming back to it.
*** Teraum's Calendar
#+INDEX: Teraum!calendar!"Teraum's Calendar"
The calendar used by most everyone on Teraum has 365.25 days each year (just like ours,) 12 months each year (just like ours,) and the annual seasons (just like ours.)
*** A Brief History of Teraum
Around 54,000 years ago, the gods from across the multiverse got together. They were having an issue managing the various creatures, plants, artifacts, and other such creations that came from being gods. They came up with the plan to store their excess and unwanted creations in, essentially, a vast zoo and museum. This would keep the things and creatures out of the way, while still letting the gods show them off to one another.

As the museum was a rather industrial-looking place full of corridors and different habitats and archives, the gods decided to build a proper planet around the museum, with oceand and continents, pine trees and salmon, a sun and moon, that sort of stuff. The world was named Teraum, though the etymology in Earth languages is coincidental, and the museum underneath it was named the Worldkeep.

It didn't take long before the gods got bored of the Worldkeep and stopped visiting. The complex began to fall into disrepair. About 30,000 years , the walls between the Worldkeep and the rest of Teraum began to fracture. The first creatures to escape the Worldkeep were giant spiders.

Soon more creatures followed, setting up homes for themselves across the geography of Teraum. With them, magic, a physical substance imbued in the Worldkeep, began to enter the world, working its way through the ground like veins of ore.
******* Humans on Teraum
#+index: Teraum!humans!"Humans on Teraum"
Humans were put inside the Worldkeep along with the other species, but they're quite a bit different. The others, elves, halflings, goblins, talking trees, they're all magic. They have magic in their blood, or sap, and it makes them special in whatever way they're special.

Humans are not magic. They are mundane. In many parts of the multiverse, those universes that are mundane, this enabled humans to thrive where other sapient life would fail, since the didn't rely on magic to be clever.

But in Teraum, a world rife with magic, humans were at a disadvantage. They were still able to escape the Worldkeep, but they were unable to hold land agianst any of the more powerful magic races. They were forced to be travelers surviving off what they could forage.

Despite the relative difficulty, humanity managed to spread across a large partof the world, and over time gained a foothold in the region that would become known as the Green Delta. (From here on, I'll use a place's contemporary name, unless there's good reason otherwise. I'll cover what contemporary means shortly.

With permanent settlements, humans began to cultivate and shape their environment, and soon had the resources to challenge their nearest neighbors: the goblins in the southward Widewoods, and the hill dwarves in the eastward Central Plains.

As the human's settlements grew, they found themselves with novel problems. Cities were racked with disease, class exploitation was rampant, and humanity found itself unable to expand any further.
******* Brief History of the Magic Revolution
#+index: Teraum!Magic Revolution!"Brief History of the Magic Revolution"
It's unclear, that is, I've written contradicting explanations of, how humans came to use magic, but at some point about one-hundred fifty years ago, a clever human realized if you put magic under pressure, it got hot.

Magic quickly became the fuel for foundries which churned out vast quantities of increasingly pure steel, and some humans even learned how to do more, well, magic things, with magic.

The period was known as the Magic Revolution, and it was a time when humans, for the first time in Teraum's history, felt as though they were equals to the other species. Their prosperity allowed their largest city, Ack, to become the largest port in the known world, and catalyzed the development of financial and civic sciences.
******* A Brief History of the Breaking
#+index: Teraum!Breaking, the!"A Brief History of the Breaking"
After nearly a century of growth, humans learned something new about magic.

If too much magic is gathered in one place, such as in a bank vault, it causes all magic to use itself up. this happened, in an event called the Breaking.

Magic is difficult for intelligent species to predictably use. When magic uses itself, the results are beyond unpredictable, well into the realm of improbable. I'll skip the details of the Breaking for now, to focus on the most important effect.

Elves, dwarves, goblins, halflings, orcs, and giants spiders are all amgic creatures. They need magic to survive, and without it, the species' lose their "spark."

Many died. Many became abominations, twisted by their magic, and were killed by fearful humans seeking survival.

Some, the less magic, were left less changed. Elves became feral, hunting their vast forests like packs of wolves. They hunted down the halflings, who became docile and dumb, until there were no more halflings. The dwarves, long-since pushed back to the mountains by human expansion, were inaccessible past their giant fortress doors.

But, humanity was mundane, so they survived the Breaking. The survivors had children, and these children grew up in a world filled with riches that were absolutely free for the taking. Humans moved ontot he halflings' farms, raided old goblin hordes, and used the riches to rebuild.

This led to a period of war between the factions of humanity, which continues to the contemporary era, eighty years after the Breaking.

Parts of the world are entering a new era of peace and prosperity, under the banner of the Red Union, but there are rumors that, in the more wild corners of the world, magic is coming back.
*** A Very Brief Summary of Teraum
Magic is a physical substance, and there are lots of magic creatures on the planet that got there from the Worldkeep, a museum-zoo buried deep underground. There are humans too, but they're not magic. But, they learn to use magic. Then they cause an apocalypse for everyone but themselves and are struggling to deal with that.
* Narratives
  :PROPERTIES:
  :EXPORT_HUGO_SECTION: stories
  :END:
** Tales from Teraum #1: "The Man with Light"
   :PROPERTIES:
   :EXPORT_FILE_NAME: tales-from-teraum-1
   :END:
*** Scene One
#+INDEX: 44bc!Sleeting, 44bc!2nd of Sleeting, 44bc!"Scene One" in /Tales from Teraum #1: "The Man with Light"/
#+INDEX: Caliper Street!114 Caliper Street!"Scene One" in /Tales from Teraum #1: "The Man with Light"/
#+INDEX: Finely, Ben!"Scene One" in /Tales from Teraum #1: "The Man with Light"/
Ben didn't dislike his job, even on days like this, when it seemed like the clouds were working overtime to pull up the ocean and drop it on his head. The pay was enough to keep him living on the north side of the river, and just last week he'd let out his belt another notch.

The work was simple enough: maintain the lampposts on the few blocks he had been assigned to. Usually that just meant refilling the oil and replacing wicks. If a lantern was damaged, he would mark it with a stick of chalk.

Ben's route took him through the back corners of the city's Brass Ward, where bureaucrats and craftsmen maintained the industry that supplied the ward's high street with goods for sale. He preferred it to the busier streets, and with today's rain, the streets were nearly empty.
#+END
-----
#+BEGIN: Introducing Sendvogue's Laboratory
One of Ben's favorite buildings on his route was 114 Caliper Street. A lean wooden building, its black paint put it in contrast to the brightly painted workshops of jewelers and offices of accountants that surrounded it.

Unlike many buildings around, it had no banner or sign, except its numberplate, and its windows were shuttered closed. For the past few months, cerulean light had leaked through those shutters, and on rainy evenings like this, the brick street cast the light back up, giving every passerby a pallor.
#+end
*** Scene Two
#+BEGIN: Sendvogue Leaves Lab, Goes to Twisted Alembic
114 Caliper Street was the home and workshop of Dr. Altar Sendvogue. He, himself, had been a lampworker in the Brass Ward as a younger man. But he hadn't enjoyed his job as much as Ben did, and was always looking for shortcuts. He'd created the small gears that let him turn a screw to lengthen the wick, and he had been promoted.

In the time since he'd invented better glass panels.
#+END
#+BEGIN: Sendvogue Brags About Lumorb Prototype
#+END
#+BEGIN: Ben Observes Sendvogue's Lab, Destroyed
#+END
#+BEGIN: Sendvogue Draws Schematics on Napkin
#+END
#+BEGIN: Giniper Meets Sendvogue at Deli
#+END
#+BEGIN: Ben Responds to Ad for Part-time Work, Hanging Posters
#+END
#+BEGIN: Ben Walks Around, Owner of Poster Company, Chandlers Guild Laid of Lamppost workers
#+END
* Supplements
