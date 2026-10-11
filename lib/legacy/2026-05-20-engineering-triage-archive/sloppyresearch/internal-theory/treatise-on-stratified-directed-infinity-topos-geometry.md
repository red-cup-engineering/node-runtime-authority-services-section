+++
# ===== IDENTITY =====
id = "treatise-on-stratified-directed-infinity-topos-geometry"
title = "Treatise on Stratified Directed ∞-Topos Geometry"
aliases = []

# ===== AUTHORIAL =====
authors = ["emsenn"]
date_created = "2025-11-09"
date_modified = "2025-11-09"
status = "draft"

# ===== CLASSIFICATION =====
document_type = "foundational_treatise"
topics = ["relationing", "topos-theory", "geometry"]
disciplines = ["mathematics"]

# ===== CITATIONS - INTERNAL =====
cites_internal = []
cited_by_internal = []

# ===== RELATIONAL METADATA =====
depends_on = []

# ===== PUBLICATION =====
published = false
+++



## Preliminaries and Model Framework


### Ambient Model

We model ∞-categories by **quasi-categories**, i.e. simplicial sets with the Joyal model structure.  

External (co)limits, Kan extensions, and fibrations are computed in this setting.

Internal reasoning occurs within a fixed **cohesive ∞-topos** $\mathfrak{E}$.

Let $(\Sigma \dashv \square \dashv \Pi)$ be the standard cohesive adjoint triple of modalities satisfying:

1.  $\Sigma$ and $\Pi$ are left- and right-exact;
2.  $\square : \mathfrak{E} \to \mathfrak{E}$ is a left-exact reflective modality with unit $\eta : \mathrm{id} \to \square$;
3.  Each modality is definable in the internal language of $\mathfrak{E}$.

All internal ∞-categorical constructions below are interpreted in $\mathfrak{E}$ via its homotopy type theory (HoTT).


### Logical Conventions

-   $\|{-}\|$ denotes propositional truncation.
-   $\simeq$ denotes homotopy equivalence (internal to $\mathfrak{E}$).
-   “Locally constant” and “coherent” are defined with respect to the internal logic of $\mathfrak{E}$.


### Reference Frameworks

1.  Lurie – **Higher Topos Theory (HTT)**
2.  Schreiber – **Cohesive ∞-Topoi**
3.  Grandis & Fajstrup – **Directed Homotopy Theory I–III**
4.  Shulman et al. – **Modal Homotopy Type Theory**


## Components


### Stratified Directed Bases

-   Axiom, Stratified Directed ∞-Site (A1)

    <div class="definition" id="org8a7d459">
    <p>
    A <b>stratified directed ∞-site</b> is a tuple $(\mathcal{X}, S, p, \square)$ where:
    </p>
    
    <ol class="org-ol">
    <li>$\mathcal{X}$ is an ∞-category with Grothendieck topology $\mathcal{J}$;</li>
    <li>$S$ is a finite poset (of <b>strata</b>);</li>
    <li>$p:\mathcal{X}\to S$ is a <b>stratification functor</b>, whose fiber $\mathcal{X}_\sigma:=p^{-1}(\sigma)$ is a full sub-∞-category;</li>
    <li>$\square:\mathcal{X}\to\mathcal{X}$ is a left-exact reflective endofunctor with unit $\eta:\mathrm{id}\Rightarrow\square$ satisfying:
    <ol class="org-ol">
    <li><b>(Directedness)</b> $\mathrm{Im}(\square)$ is a wide subcategory stable under pullback and composition, with all non-identity morphisms non-invertible;</li>
    <li><b>(Strata Monotonicity)</b> if $\sigma\le\tau$ in $S$, then $\eta$ restricts $\mathcal{X}_\sigma\to\square(\mathcal{X}_\tau)$ and is $p$-monotone.</li>
    </ol></li>
    </ol>
    
    <p>
    A <b>morphism</b> $(\mathcal{X},S,p,\square)\to(\mathcal{Y},T,q,\square')$ is a continuous functor $f:\mathcal{X}\to\mathcal{Y}$ preserving covers, strata (via a monotone map $S\to T$), directed maps, and equipped with a modal natural isomorphism $f\circ\square\simeq\square'\circ f$.
    </p>
    
    </div>

-   Lemma, Exit ∞-Functor

    <div class="lemma" id="org4e44c1e">
    <p>
    Let $(\mathcal{X},S,p,\square)$ be a stratified directed ∞-site.  
    Define the <b>exit ∞-category</b> $\mathrm{Exit}_\infty(\mathcal{X})$:
    $$
    \mathrm{Map}_{\mathrm{Exit}_\infty(\mathcal{X})}(\sigma,\tau)
     := \underset{x\in\mathcal{X}_\sigma,\,y\in\mathcal{X}_\tau}{\mathrm{colim}}
        \mathrm{Map}_{\mathcal{X}}(x,\square y).
    $$
    Then $\mathrm{Exit}_\infty$ extends to a functor
    $$
    \mathrm{Exit}_\infty:\mathbf{StratDir}_\infty\to\mathbf{Cat}_\infty.
    $$
    </p>
    
    </div>

-   Lemma, Skeletal Filtration

    <div class="lemma" id="org462039e">
    <p>
    If $S$ carries a rank function $\dim:S\to\mathbb{N}$,
    then $\mathcal{X}$ admits a filtration
    $$
    \mathrm{Sk}_0\mathcal{X}\subset
    \mathrm{Sk}_1\mathcal{X}\subset\cdots\subset\mathcal{X},
    $$
    where $\mathrm{Sk}_n\mathcal{X}:=p^{-1}(\{\sigma\mid\dim(\sigma)\le n\})$.
    </p>
    
    </div>


### Part III. Constructible and Coherent Diagrams

-   Definition, Constructible Diagram

    <div class="definition" id="org57e95a9">
    <p>
    Given $(\mathcal{X},S,p,\square)$ and a stable presentable $&infin;$-category $\mathcal{E}$ internal to $\mathfrak{E}$,
    define
    $$
    \mathrm{Constr}(\mathcal{X},\mathcal{E})
     := \mathrm{Fun}^{\mathrm{loc}}_{\square}
        (\mathrm{Exit}_\infty(\mathcal{X}),\mathcal{E}),
    $$
    the ∞-category of <b>locally constant</b> and $\square$-covariant diagrams.
    </p>
    
    </div>

-   Definition, Coherent Diagram

    <div class="definition" id="org7ad80a7">
    <p>
    A diagram $F\in\mathrm{Constr}(\mathcal{X},\mathcal{E})$ is <b>coherent</b>
    if for every object $x$ in $\mathrm{Exit}_\infty(\mathcal{X})$
    the canonical map
    $$
    \eta_x : F(x) \to \mathrm{hocolim}\,F
    $$
    is an equivalence in $\mathcal{E}$.
    </p>
    
    </div>

-   3.3 Assumption (Exit Cofinality)

    <div class="assumption" id="org712b765">
    <p>
    $\mathrm{Exit}_\infty(\mathcal{X})$ is weakly contractible,
    for instance if $S$ has a maximum stratum and every $\sigma$ admits a directed morphism $\sigma\to\tau_{\max}$.
    </p>
    
    </div>

-   3.4 Theorem (Coherence Criterion)

    <div class="theorem" id="orgc905cdc">
    <p>
    If $\mathrm{Exit}_\infty(\mathcal{X})$ is weakly contractible
    and $F$ is locally constant,
    then for any $x$,
    $$
    F(x)\simeq\mathrm{hocolim}\,F.
    $$
    </p>
    
    </div>


### Part IV. The ∞-Topos of Coherence

-   4.1 Definition (∞-Topos of Coherence)

    <div class="definition" id="org8de6cef">
    <p>
    Let $\mathfrak{E}_{\mathcal{X}}$
    be the full sub-∞-category of $\mathrm{Constr}(\mathcal{X},\mathcal{E})$
    consisting of coherent diagrams.
    It is an ∞-topos, realized as the left-exact accessible localization
    $$
    \mathfrak{E}_{\mathcal{X}}
     \;\simeq\;
     L_S\mathrm{Constr}(\mathcal{X},\mathcal{E}),
    $$
    where $L_S$ inverts the set of canonical maps $\{\eta_x\}$.
    </p>
    
    </div>

-   4.2 Proposition (Stability Under Directed Morphisms)

    <div class="proposition" id="org4470970">
    <p>
    For any directed natural transformation $\Phi:F\to F'$ in $\mathfrak{E}_{\mathcal{X}}$,
    $$
    \eta_x\ \text{equivalence for }F
     \;\Rightarrow\;
     \eta_x\ \text{equivalence for }F',
    $$
    and $\mathrm{hocolim}\,F\to\mathrm{hocolim}\,F'$ is a modal equivalence.
    </p>
    
    </div>

-   4.3 Definition (Field Object)

    <div class="definition" id="org5ed5336">
    <p>
    Assuming $\mathcal{E}$ complete,
    define the <b>field object</b>
    $$
    \mathcal{F}:=\mathrm{holim}_{F\in\mathfrak{E}_{\mathcal{X}}}F.
    $$
    </p>
    
    </div>

-   4.4 Axiom A2 (Ambidextrous Invariance)

    <div class="axiom" id="orgb4faee5">
    <p>
    If $\mathcal{E}$ is symmetric monoidal stable with dualizable objects of $F$,
    then
    $$
    \mathrm{holim}\,\mathcal{F}\simeq\mathrm{hocolim}\,\mathcal{F},
    $$
    expressing modal fixed-point equivalence for $\square$.
    </p>
    
    </div>

-   4.5 Corollaries

    <div class="corollary" id="org764ee4e">
    <ol class="org-ol">
    <li>(Global–Local Equivalence) For coherent $D$, $\mathrm{holim}\,D\simeq\mathrm{hocolim}\,D$.</li>
    <li>(Stability Under Kan Extension) Coherence is preserved by directed Kan extensions.</li>
    </ol>
    
    </div>


### Part V. Duality and Ambidexterity

-   5.1 Definition (Dual Diagram)

    <div class="definition" id="org382455c">
    <p>
    Let $\mathcal{E}$ be symmetric monoidal stable.
    For $F:\mathrm{Exit}_\infty(\mathcal{X})\to\mathcal{E}$
    with pointwise dualizable values, define
    $$
    F^{\vee}:\mathrm{Exit}_\infty(\mathcal{X})^{\mathrm{op}}\to\mathcal{E},
    \quad
    F^{\vee}(x):=\underline{\mathrm{Hom}}(F(x),1).
    $$
    </p>
    
    </div>

-   5.2 Theorem (Verdier Ambidexterity)

    <div class="theorem" id="orgf13a39d">
    <p>
    If $\mathrm{Exit}_\infty(\mathcal{X})$ is finite and $F$ pointwise dualizable,
    then
    $$
    \mathrm{hocolim}\,F\simeq\mathrm{holim}\,F^{\vee}.
    $$
    <b>Proof.</b>  By coend–end duality in a symmetric monoidal stable category and the adjunction
    $$
    \mathrm{Map}(1,\mathrm{holim}\,F^{\vee})
     \simeq
     \mathrm{Map}(\mathrm{hocolim}\,F,1).
    $$
    </p>
    
    </div>

-   5.3 Corollaries

    <div class="corollary" id="orgd28ea19">
    <ol class="org-ol">
    <li>$F$ coherent ⇔ $F^{\vee}$ coherent;</li>
    <li>Dualization induces a contravariant equivalence</li>
    </ol>
    
    <p>
    $$
    (-)^{\vee}:\mathfrak{E}_{\mathcal{X}}^{\mathrm{op}}\simeq\mathfrak{E}_{\mathcal{X}}.
    $$
    </p>
    
    </div>


### Part VI. Dynamics (Kan Extensions and Fibrations)

-   6.1 Definition (Homotopy Kan Extensions)

    <div class="definition" id="org5e689cc">
    <p>
    Given $\Phi:\mathrm{Exit}_\infty(\mathcal{X})\to\mathrm{Exit}_\infty(\mathcal{Y})$
    and $F:\mathrm{Exit}_\infty(\mathcal{X})\to\mathcal{E}$,
    define $\mathrm{LKan}_\Phi F$ and $\mathrm{RKan}_\Phi F$
    by the standard universal properties.
    </p>
    
    </div>

-   6.2 Lemma (Stability Under Cofinal Maps)

    <div class="lemma" id="orge405164">
    <p>
    If $\Phi$ is cofinal (resp. coinitial),
    then
    $$
    \mathrm{hocolim}\,F\simeq\mathrm{hocolim}\,\mathrm{LKan}_\Phi F
    \quad
    (\text{resp. }\mathrm{holim}\,F\simeq\mathrm{holim}\,\mathrm{RKan}_\Phi F).
    $$
    Hence coherence is preserved under such $\Phi$.
    </p>
    
    </div>

-   6.3 Definition (Condition Fibration)

    <div class="definition" id="org7b8b5de">
    <p>
    Define the <b>condition fibration</b>
    $$
    \mathrm{Cond}:\mathfrak{E}_{(-)}\to\mathbf{StratDir}_\infty
    $$
    as the Grothendieck construction of the pseudofunctor
    $\mathcal{X}\mapsto\mathfrak{E}_{\mathcal{X}}$
    with reindexing $f_!:={\mathrm{LKan}}_f$.
    </p>
    
    </div>

-   6.4 Theorem (Dynamic Invariance of $\mathcal{F}$)

    <div class="theorem" id="org241a846">
    <p>
    Under A2 and 6.2,
    $\mathrm{holim}\,\mathcal{F}\simeq\mathrm{hocolim}\,\mathcal{F}$
    is stable up to modal equivalence for all directed $\Phi$.
    </p>
    
    </div>


## Part VII. Axiomatic Summary and Meta-Framework


### 7.1 Axioms

<div class="axiom" id="orgc9eaee1">
<ul class="org-ul">
<li>A1 (Stratified Directed Cohesive Base)</li>
<li>A2 (Modal Ambidextrous Invariance)</li>
<li>A3 (Verdier Duality under Dualizable Targets)</li>
<li>A4 (Cohesive Ambidexterity)</li>
</ul>

</div>


### 7.2 Derived Theorems

<div class="theorem" id="org16de257">
<p>
T₁ (Coherence Criterion)  
T₂ (Verdier Ambidexterity)  
T₃ (Dynamic Invariance)
</p>

</div>


### 7.3 Model Interpretations

1.  **Cohesive Topoi**: stratified directed manifolds with conical stratifications.
2.  **Modal HoTT**: types with directed modal operator $\square$.
3.  **Directed Simplicial Sets**: $\mathrm{Exit}_\infty$ interpreted as Grandis’ $d$-spaces.

