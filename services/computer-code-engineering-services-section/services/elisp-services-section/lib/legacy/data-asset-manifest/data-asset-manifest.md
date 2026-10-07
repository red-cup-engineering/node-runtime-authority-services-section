# Data Asset Manifest (early draft)
## Table of Contents

-   [Introduction](#introduction)
-   [Data Asset Manifest](#org80730fa)
    -   [Data Asset Manifest Structure](#org98a38e8)
        -   [Creator](#orgf623306)
        -   [Descrption](#org4471dc0)
        -   [License](#org4d21528)
        -   [Name](#org430095c)
        -   [Versions](#org2c5a3f6)
    -   [Data Asset Manifest Channel Structure](#org65c4f2e)
    -   [Example Data Asset Manifest Channel](#example-data-asset-manifest-channel)
    -   [Functions](#orgf0753b0)
        -   [Overview](#orgea46308)
        -   [Channel Functions](#orgc2a92ea)
        -   [Manifest Functions](#orga3f8c53)
-   [Suppplements](#org1d89708)
    -   [Index](#org9ea4ed5)
    -   [README](#org160bf55)
        -   [Data Asset Manifest](#orgaab49c1)
    -   [Source](#org545e248)


<a id="introduction"></a>

## Introduction

This proposal is about a prototype specification. It is likely to be incomplete, self-contradicting, and flawed.

This proposal contains the specification for a *data asset manifest* and *data asset manifest channel*, formats for maintaining a record about a piece of (implicitly digital) content and a listing of those records.

This proposal was created by me, emsenn, in the United States. To the extent possible under law, I have waived all copyright and related or neighboring rights to this document. This document was created for the benefit of the public. If you're viewing it on a remote server, you're encouraged to download your own copy. To learn how you can support me, see [https://emsenn.net/donate](https://emsenn.net/donate).


<a id="org80730fa"></a>

## Data Asset Manifest

A *data asset manifest* is a record of information about a *data asset*, an (implicitly digital) resource such as an essay or illustration. The record, or *manifest*, includes at least information about available *versions* and *sources* of the *asset*, and may include information about its *title*, *creator*, *license*, and more.

```elisp
'("shaggy-dog-tale"
  ("versions"
   ("current"
    ("sourcehut"
     ("location" . "https://example.org/shaggy-dog-tale/")
     ("formats" . ("html"))))))
```

This example includes all of the *manifest's* required elements, and nothing else. The *identifier* of the *data asset* is `shaggy-dog-tale`, it has a single version called `current` available, whcih is available at a single source, `sourcehut`, which stores the *asset* at `https://emsenn.org/shaggy-dog/tale/` in a single format, `html`.

A *data asset manifest channel* is a list of *manifests* without duplicate *identifiers*.

A note on convention. Many variables (including function names) will be prefixed with `dam-`. This an initialism of *data asset manifest*, and its use as a prefix is a convention in *Emacs Lisp* to avoid contaminating the general namespace.


<a id="org98a38e8"></a>

### Data Asset Manifest Structure

This section explains all recognized elements of a *data asset manifest*.


<a id="orgf623306"></a>

#### Creator


<a id="org4471dc0"></a>

#### Descrption


<a id="org4d21528"></a>

#### License


<a id="org430095c"></a>

#### Name


<a id="org2c5a3f6"></a>

#### Versions


##### Source


###### Formats


###### Location


<a id="org65c4f2e"></a>

### Data Asset Manifest Channel Structure

A *data asset manifest channel* is a list of *data asset manifests*. In the future it may include information abotu the channel, such as contact information for its maintainer.


<a id="example-data-asset-manifest-channel"></a>

### Example Data Asset Manifest Channel

This is my actual *manifest channel*, that I'm maintaining as I develop this specification.

```elisp
(setq dam-example-channel
      '(("brutstrap-css"
	 ("name" . "Brutstrap CSS")
	 ("description" . "a cascading stylesheet for representing HTML content as it is constructed.")
	 ("creator" . "emsenn")
	 ("license" . "CC0")
	 ("versions"
	  ("current"
	   ("sourcehut"
	    ("location" . "https://git.sr.ht/~emsenn/brutstrap-css/blob/master/")
	    ("formats" . ("html" "md" "pdf" "tex" "txt"))))))))
```


<a id="orgf0753b0"></a>

### Functions


<a id="orgea46308"></a>

#### Overview

The following sections contains functions for working with a *data asset manifest* and *data asset manifest channel*. These functions are implemented in *Emacs Lisp*.


<a id="orgc2a92ea"></a>

#### Channel Functions


##### Get Manifests

This function builds a list of all the *identifiers* in the given *channel*.

```elisp
(defun dam-get-manifests
    (channel)
  "Return a list of the manifests recorded in CHANNEL."
  (loop for manifest
	in channel
	collect (car manifest)))
```


##### Get Manifest

This function returns the *manifest* of the given *identifier* on the given *channel*.

```elisp
(defun dam-get-manifest
    (channel id)
  "Return manifest ID from CHANNEL.)
  (assoc id channel))
```


<a id="orga3f8c53"></a>

#### Manifest Functions


##### Get Manifest Versions

```elisp
(defun dam-get-versions
    (channel id)
  "Get the declared versions of ID from CHANNEL."
  (loop for versions
	in (cdr (assoc "versions" (dam-get-manifest channel id)))
	collect (car versions)))
```


##### Get Version Sources

```elisp
(defun dam-get-sources
    (channel id version)
  "Return a list of sources for VERSION of ID."
  (loop for source
	in (cdr (assoc version (cdr (assoc "versions" (dam-get-manifest channel id)))))
	collect (car source)))
```


<a id="org1d89708"></a>

## Suppplements


<a id="org9ea4ed5"></a>

### Index

-   **data asset manifest channel:**

-   **data asset manifest:**

-   **data asset:**

-   **data asset manifest version:**

-   **data asset manifest source:**

-   **data asset manifest title:**

-   **data asset manifest creator:**

-   **data asset manifest license:**

-   **data asset manifest identifier:**

-   **Emacs Lisp:**


<a id="org160bf55"></a>

### README


<a id="orgaab49c1"></a>

#### Data Asset Manifest

This proposal is about a prototype specification. It is likely to be incomplete, self-contradicting, and flawed.

This proposal contains the specification for a *data asset manifest* and *data asset manifest channel*, formats for maintaining a record about a piece of (implicitly digital) content and a listing of those records.

This proposal was created by me, emsenn, in the United States. To the extent possible under law, I have waived all copyright and related or neighboring rights to this document. This document was created for the benefit of the public. If you're viewing it on a remote server, you're encouraged to download your own copy. To learn how you can support me, see [https://emsenn.net/donate](https://emsenn.net/donate).


<a id="org545e248"></a>

### Source

```elisp
# Introduction
  :PROPERTIES:
  :CUSTOM_ID: introduction
  :END:
{{{document-is-prototype(specification)}}}

This {{{doc}}} contains the specification for a /data asset manifest/
and /data asset manifest channel/, formats for maintaining a record
about a piece of (implicitly digital) content and a listing of those
records.

{{{document-eli(default)}}}
# Data Asset Manifest
  :PROPERTIES:
  :header-args: :results value silence :eval no-export :noweb yes :tangle ./emsems.el :padline no
  :END:
A /data asset manifest/ is a record of information about a /data
asset/, an (implicitly digital) resource such as an essay or
illustration. The record, or /manifest/, includes at least information
about available /versions/ and /sources/ of the /asset/, and may
include information about its /title/, /creator/, /license/, and more.

```elisp
  '("shaggy-dog-tale"
    ("versions"
     ("current"
      ("sourcehut"
       ("location" . "https://example.org/shaggy-dog-tale/")
       ("formats" . ("html"))))))
```

This example includes all of the /manifest's/ required elements, and
nothing else. The /identifier/ of the /data asset/ is
=shaggy-dog-tale=, it has a single version called =current= available,
whcih is available at a single source, =sourcehut=, which stores the
/asset/ at =https://emsenn.org/shaggy-dog/tale/= in a single format,
=html=.

A /data asset manifest channel/ is a list of /manifests/ without
duplicate /identifiers/.

A note on convention. Many variables (including function names) will
be prefixed with =dam-=. This an initialism of /data asset manifest/,
and its use as a prefix is a convention in /Emacs Lisp/ to avoid
contaminating the general namespace.
## Data Asset Manifest Structure
This section explains all recognized elements of a /data asset
manifest/.
### Creator
### Descrption
### License
### Name
### Versions
#### Source
##### Formats
##### Location
## Data Asset Manifest Channel Structure
A /data asset manifest channel/ is a list of /data asset manifests/.
In the future it may include information abotu the channel, such as
contact information for its maintainer.
## Example Data Asset Manifest Channel
   :PROPERTIES:
   :CUSTOM_ID: example-data-asset-manifest-channel
   :END:
This is my actual /manifest channel/, that I'm maintaining as I
develop this specification.
```elisp
  (setq dam-example-channel
	'(("brutstrap-css"
	   ("name" . "Brutstrap CSS")
	   ("description" . "a cascading stylesheet for representing HTML content as it is constructed.")
	   ("creator" . "emsenn")
	   ("license" . "CC0")
	   ("versions"
	    ("current"
	     ("sourcehut"
	      ("location" . "https://git.sr.ht/~emsenn/brutstrap-css/blob/master/")
	      ("formats" . ("html" "md" "pdf" "tex" "txt"))))))))
```
## Functions
### Overview
The following sections contains functions for working with a /data
asset manifest/ and /data asset manifest channel/. These functions are
implemented in /Emacs Lisp/.

### Channel Functions
#### Get Manifests
This function builds a list of all the /identifiers/ in the given
/channel/.
```elisp
  (defun dam-get-manifests
      (channel)
    "Return a list of the manifests recorded in CHANNEL."
    (loop for manifest
	  in channel
	  collect (car manifest)))
```
#### Get Manifest
This function returns the /manifest/ of the given /identifier/ on the
given /channel/.
```elisp
  (defun dam-get-manifest
      (channel id)
    "Return manifest ID from CHANNEL.)
    (assoc id channel))
```
### Manifest Functions
#### Get Manifest Versions
```elisp
  (defun dam-get-versions
      (channel id)
    "Get the declared versions of ID from CHANNEL."
    (loop for versions
	  in (cdr (assoc "versions" (dam-get-manifest channel id)))
	  collect (car versions)))
```
#### Get Version Sources
```elisp
  (defun dam-get-sources
      (channel id version)
    "Return a list of sources for VERSION of ID."
    (loop for source
	  in (cdr (assoc version (cdr (assoc "versions" (dam-get-manifest channel id)))))
	  collect (car source)))
```
# Suppplements
## Index
- data asset manifest channel ::
- data asset manifest ::
- data asset ::
- data asset manifest version ::
- data asset manifest source ::
- data asset manifest title ::
- data asset manifest creator ::
- data asset manifest license ::
- data asset manifest identifier ::
- Emacs Lisp ::
## README
   :PROPERTIES:
   :EXPORT_FILE_NAME: ./README
   :END:
### {{{title}}}
## Source
```
