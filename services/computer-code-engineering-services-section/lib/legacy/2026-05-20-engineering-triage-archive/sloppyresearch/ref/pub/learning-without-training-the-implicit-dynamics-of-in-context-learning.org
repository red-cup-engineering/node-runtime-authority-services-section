:PROPERTIES:
:ID:       e1f9bcb1-e6d3-4b20-a090-b09b37bbb62b
:ROAM_REFS: https://arxiv.org/abs/2507.16003 @dherin_learning_2025
:public:   true
:resource-description: (([[id:edaef069-c68d-46aa-a970-d3cb7fe3165c][resource type]] . [[id:dda1e0cb-0218-4b9b-bbd5-7435a2cef0aa][research paper]]))
:END:
#+title: Learning without training: The implicit dynamics of in-context learning
#+date: [2025-10-05 Sun 06:05]

* [[id:e7fb739f-dba6-4343-9e8d-12a4ebbd472a][resource comment]]

** Core Idea

[[id:00d4fa27-d2ea-4d21-98e2-abb17e887175][Large language models]] can learn from examples in their input ([[id:1a0f1788-1a40-4cf7-9864-afc1b6c01955][in-context learning]]) without changing their [[id:ec006c64-02c8-4b3e-a347-ee41cc4a8720][inference weights]]. This paper explains *how* that happens, mathematically: "the model's internal activations create temporary, context-dependent weight changes in its feedforward (MLP) layers." (MLP = [[id:26ed6bb2-fdc3-4fdf-996f-4ba9e894e563][multilayer perceptron]])

** Mechanisms

- transformer block = (self-attention + MLP)
- self-attention reads the prompt and produces representations of "what's relevant"[fn:: This may map near [[id:bd6a450d-95e3-4162-9c9e-05c2afba4705][kyriontoeidonics]]]
- those representations modulate the next MLP layer
  - effectively adding low-rank weight update
- So even tho no weights are actually changed, effective weight in forward pass is different than trained weight.

** What the paper shows

*** Theory

- Using a linearized approximation of the Transformer, it shows how attention outputs can induce a low-rank perturbation to the MLP's weight matrix.
- This is enough to let the model adapt to a new task as if it had learned (through training).

*** Experiments

- They test toy models and find evidence these implicit weight changes happen
- The preidcted low-rank structure matches what they observed.

** Why it matters

- Explains in-context learning without needing to claim the model "stores a new model in its activations", a common hypothesis.
- Shows that "learning without gradient updates" can arise naturally from the Transformer's structure.
- Bridges theory and observed behavior: how static weights still produce adaptive behavior.

** Limitations

- The paper uses simplified assumptions and experiment/models.
  - residuals, nonlinearities, and scale effects aren't accounted for.
- Doesn't prove the described dynamic is the main driver of in-context learning in big models.

* [[id:0638898a-ad87-4dcc-aaa7-1a0634d080e3][resource code]]

** [[id:42f66990-2e7d-4081-8f0e-7eb67b23e1fb][BibTex entry]]

#+begin_src bibtex :canonical yes
  
@misc{dherin_learning_2025,
	title = {Learning without training: {The} implicit dynamics of in-context learning},
	shorttitle = {Learning without training},
	url = {http://arxiv.org/abs/2507.16003},
	doi = {10.48550/arXiv.2507.16003},
	abstract = {One of the most striking features of Large Language Models (LLM) is their ability to learn in context. Namely at inference time an LLM is able to learn new patterns without any additional weight update when these patterns are presented in the form of examples in the prompt, even if these patterns were not seen during training. The mechanisms through which this can happen are still largely unknown. In this work, we show that the stacking of a self-attention layer with an MLP, allows the transformer block to implicitly modify the weights of the MLP layer according to the context. We argue through theory and experimentation that this simple mechanism may be the reason why LLMs can learn in context and not only during training. Specifically, we show under mild simplifying assumptions how a transformer block implicitly transforms a context into a low-rank weight-update of the MLP layer.},
	publisher = {arXiv},
	author = {Dherin, Benoit and Munn, Michael and Mazzawi, Hanna and Wunder, Michael and Gonzalvo, Javier},
	month = jul,
	year = {2025},
	note = {arXiv:2507.16003 [cs]},
	keywords = {Computer Science - Computation and Language, Computer Science - Machine Learning},
}
#+end_src
