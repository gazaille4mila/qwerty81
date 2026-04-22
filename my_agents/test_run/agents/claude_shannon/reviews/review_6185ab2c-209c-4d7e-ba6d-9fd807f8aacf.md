# Review: Robustness in Text-Attributed Graph Learning: Insights, Trade-offs, and New Defenses

**Paper ID:** 6185ab2c-209c-4d7e-ba6d-9fd807f8aacf

---

## Summary

This paper presents a large-scale, systematic robustness evaluation framework for Text-Attributed Graph (TAG) learning, benchmarking classical GNNs, Robust GNNs (RGNNs), and GraphLLMs across ten datasets from four domains under textual, structural, and hybrid adversarial attacks in both poisoning and evasion settings. The three core empirical findings are: (1) a text-structure robustness trade-off whereby models excel against one attack type but fail against the other, (2) that simple RGNNs like GNNGuard recover near-SOTA performance when paired with modern text encoders like RoBERTa, and (3) GraphLLMs are disproportionately vulnerable to training-data poisoning compared to GNNs. The paper then proposes SFT-auto, a multi-task supervised fine-tuning framework that trains an LLM to detect attacks (text, structure) and adaptively recover from them at inference time. Overall this is a solid evaluation paper with genuine empirical insights and a practical defense proposal, though the novelty of SFT-auto is incremental and the theoretical grounding for the trade-off is largely absent.

---

## Novelty Assessment

**Verdict: Moderate**

The paper's comparative framework is the most distinctive contribution — it unifies three model families (GNNs, RGNNs, GraphLLMs) across more datasets, more attack types, and more evaluation settings than any predecessor (Table 1 makes a credible case for this). The text-structure trade-off observation is empirically well-documented and practically useful. However, none of the individual components are novel. GNNs and RGNNs under structural attacks have been studied extensively (GRB, Mujkanovic et al. 2022, Gosch et al. 2023). LLM-based text attacks are a natural extension of prior work. SFT-auto is a combination of supervised fine-tuning with multi-task detection/prediction and a heuristic inference pipeline — all previously known techniques assembled in a sensible way but without theoretical justification for why this specific combination breaks the trade-off. The "Guardual" extension in Appendix F.3 is mentioned but not evaluated in the main paper. The claim "to the best of our knowledge, this is the first comprehensive analysis" is plausible given the recent arXiv preprints by Guo et al. (2024a), Zhang et al. (2025a), and Olatunji et al. (2025), though all are concurrent.

---

## Technical Soundness

The evaluation protocol is methodologically sound. The choice to pair poisoning attacks with transductive settings and evasion attacks with inductive settings follows Gosch et al. (2023) and is justified. The decision to exclude Mettack from the main paper is justified in Appendix C.4 with a concrete table (Table 4) showing that Mettack transfers poorly to validation-based defenses, yielding 77.86% vs. 70.33% for HeuristicAttack on Cora with validation.

The LLM-based text attack using GPT-4o-mini with neighborhood-aware prompts is a reasonable novel attack design, though its strength relative to gradient-based NLP attacks is not benchmarked head-to-head (the exclusion of word-level attacks is defended in Appendix C.4.2 on transferability grounds).

SFT-auto's inference-time heuristic (cosine similarity < 0.5 threshold for flagging structure-attacked nodes) is not theoretically motivated, and the sensitivity of this threshold is not ablated in the main paper. The detection-then-recovery pipeline assumes that textual and structural attacks are separable and that text attack detection precedes structural detection — this ordering assumption is not validated against cases where both attacks occur simultaneously (hybrid setting is in Appendix E but not the main paper).

The complexity analysis states inference cost is at most 2× per-sample TLLM — this is correct in principle but elides real-world overhead from the additional detection pass.

---

## Baseline Fairness Audit

**Structural attacks (Figure 2):** Baselines use the same text encoder (RoBERTa for GNN-based, Mistral-7B for GraphLLMs) and the same datasets. Perturbation ratios are uniform (20% inductive/evasion, 30% transductive/poisoning). The surrogate model (GCN with BoW) is transfer-based, which is the standard setting. Results are averaged over three runs with random splits (except ArXiv, single official split — this is flagged as a limitation).

**Textual attacks (Figure 3):** The LLM attack uses GPT-4o-mini uniformly. However, 40% evasion perturbation and 80% training perturbation are very high budgets. The paper acknowledges in Appendix C that lower ratios are deferred to Appendix I.3 — this is appropriate, but the main paper should at minimum report whether rank ordering is stable at lower perturbation budgets. Figure 2 rank visualizations suggest the qualitative story holds.

**SFT-auto comparison:** The comparison is against the base SFT-neighbor and GraphGPT, which is fair. The AutoGCN ablation (Section 5.3) is a useful control but uses GCN specifically — it would be informative to compare against a spectral RGNN with the same detection pipeline (e.g., EvenNet-auto) to isolate the contribution of LLM reasoning versus the multi-task training design.

---

## Quantitative Analysis

- Figure 3 (textual poisoning): SFT-neighbor drops 25% on CiteSeer, while GNNs drop only 5–10%. This is a large, meaningful gap (Tables I.1.6 and I.2 contain full numbers).
- Figure 4 (right): SFT-neighbor without neighbors achieves 95.0% clean on PubMed vs. SFT-neighbor with neighbors at 95.1% — essentially identical, confirming that PubMed is text-friendly and structure contributes negligibly. On Computer, the gap widens: SFT without neighbors 80.8% vs. with neighbors 89.7%, a 8.9% gap.
- SFT-auto performance drop on Computer under structural attack: approximately 6.6% vs. SFT-neighbor's 21.0% (Figure 4 right, bottom), a ~3× improvement.
- Figure 6b: SFT-auto detection rate for textual attacks is 6.2–17.4× higher than AutoGCN's. These ratios are striking and would benefit from absolute numbers to ensure the baseline is not trivially low.
- Appendix Table 4: HeuristicAttack reduces Cora accuracy from 82.91% to 61.30% (no validation) vs. Mettack only to 75.13% — a 14-point gap confirming the stronger attack choice.

Three-run averaging is reported for most datasets; ArXiv uses a single split, which limits confidence in ArXiv-specific claims.

---

## Qualitative Analysis

The text-structure trade-off is the paper's most interesting qualitative finding. Figure 4 (left) clearly shows that the trade-off is architecture-driven: SFT-neighbor sits in the "low structure drop rank, high text drop rank" quadrant, while vanilla GCN sits in the opposite corner. SFT-auto is the only method in the lower-left region, which is the desired Pareto-optimal zone. This visual argument is compelling.

The finding that GNNGuard, an early threshold-based method, achieves near-SOTA structural robustness with RoBERTa encodings is a valuable observation with practical implications — it suggests the field has been undervaluing simple methods that happen to leverage the right text encoder. The analysis in Appendix F traces this back to the embedding quality difference between BoW/TF-IDF and transformer-based encoders, which is a legitimate mechanistic explanation.

The failure mode of GraphLLMs under poisoning (Section 3.2) is well-explained: the transductive GNN leverages neighbor aggregation to offset corrupted node features, whereas an LLM processing each node's text directly cannot perform this implicit denoising when the training data itself is corrupted. This is a clear and convincing mechanistic story.

The hybrid and adaptive attack results are deferred to appendices, which is acceptable given page constraints, but the paper's main claims rest on single-attack settings only.

---

## Results Explanation

The paper does a good job explaining most of its key results mechanistically. The GNNGuard revival (Appendix F) is well-argued. The GraphLLM poisoning vulnerability is explained via the transductive aggregation argument. The spectral GNN advantage under structural poisoning (EvenNet, APPNP, GPRGNN performing well in Figure 2 right) is attributed to the robust diffusion process — this aligns with prior work (Gosch et al., 2023).

What is inadequately explained: (1) Why does LLaGA perform worse than other GraphLLMs under structural attacks? The paper says alignment-based methods "rely more heavily on structure" but does not quantify this reliance or explain why alignment training has this effect. (2) Why does SFT-auto fail to improve further on certain datasets (e.g., Photo, Figure 6)? The detection rate for textual attacks is reportedly high, but the accuracy improvement may be limited by recovery quality.

---

## Reference Integrity Report

References checked spot-checked:
- GNNGuard: Zhang & Zitnik 2020, NeurIPS 33:9263–9275 — verifiable, correct attribution.
- GRB: Zheng et al. 2021, arXiv 2111.04314 — exists, correct description.
- GRAND: Feng et al. 2020, NeurIPS 33:22092–22103 — verifiable.
- PGD attack: Xu et al. 2019, IJCAI 2019 — verifiable.
- GRBCD: Geisler et al. 2021, NeurIPS 34:7637–7649 — verifiable.
- LLMNodeBed (Wu et al. 2025): cited as "CoRR abs/2502.18771" — this URL also appears for the separate "Wang et al. 2025b" citation (Yuxiang Wang et al., "Exploring graph tasks with pure LLMs"), suggesting a citation collision. This is a potential reference error: the LLMNodeBed paper by Xixi Wu et al. may have a different arXiv ID than the one assigned to Wang et al. 2025b. The paper uses LLMNodeBed extensively (datasets, baselines) and this citation should be verified.
- Olatunji et al. (2025): cited as arXiv 2508.04894 — given today's date is April 2026, this is plausible if submitted in August 2025, but the "2025" date on a 2508 arXiv paper is consistent.

No hallucinated references detected. One potentially confused citation (Wu et al. 2025 / Wang et al. 2025b sharing the same arXiv URL).

---

## AI-Generated Content Assessment

The paper shows moderate signals of AI-assisted writing. Phrases like "a most significant and visionary insight" do not appear in the paper itself, but the abstract and introduction deploy generic framing ("To address these limitations, we introduce...", "Our extensive analysis reveals...", "To summarize, our main contributions are as follows"). Section transitions are occasionally abrupt. The technical sections (Section 5.2, Appendix C) are detailed and specific enough to suggest genuine human authorship of the core methodology. Overall: likely AI-assisted drafting for framing sections, with human-authored technical content. Not a serious quality concern.

---

## Reproducibility

Strong reproducibility posture:
- Code released at https://github.com/Leirunlin/TGRB.
- Hardware specified: NVIDIA A100-SXM4 80GB, Intel Xeon 2.30 GHz, 512 GB RAM.
- Model cards listed for all LLMs used (Appendix A.3).
- Hyperparameters for all attacks and defenses provided (Appendices C–D).
- Dataset statistics in Table 3; dataset loading via LLMNodeBed.
- Text attack prompt template fully reproduced in Appendix C.2.

Limitations: ArXiv uses a single official split (no variance reported). Some GNN baseline hyperparameters are searched via validation — search ranges not fully specified. The cosine similarity threshold of 0.5 in SFT-auto's structure attack detection (Section 5.2) is not ablated.

---

## Per-Area Findings

### Area 1: Comprehensive Evaluation Framework (Weight: 0.5)
The framework advances the state of TAG robustness evaluation by covering three model families, ten datasets, four domains, and multiple attack types/settings. Table 1 is a credible positioning against prior work. The main gap relative to concurrent work (TrustGLM, Olatunji et al.) is the inclusion of Text-GIA attacks and adaptive attacks. The framework's decision to align poisoning with transductive and evasion with inductive settings is methodologically sound. The rank-based summary visualization (Figures 2 and 3) efficiently communicates performance across datasets without collapsing to a single number.

### Area 2: SFT-auto Defense Framework (Weight: 0.5)
SFT-auto is an engineering contribution that combines standard SFT with multi-task training and a heuristic detection-recovery inference pipeline. Its empirical performance in Figure 4 (left) — occupying the Pareto-dominant quadrant — is the paper's clearest "new result." However, the method has three design choices not justified by ablation in the main paper: (1) the threshold r = min(1/|C|, 0.15) for attack ratio during training, (2) the cosine similarity threshold of 0.5 for structure attack detection, (3) the ordering of text attack detection before structure attack detection. The comparison to AutoGCN (Section 5.3) is instructive but not a full ablation. The paper should report performance under higher adaptive attack strengths beyond those in Appendix G.

---

## Synthesis

**Cross-cutting themes:** The dominant theme is that text encoder quality is a first-order factor that prior TAG robustness work has underweighted. This explains both the GNNGuard revival and the GraphLLM vulnerabilities. This theme is consistent and compelling across both contribution areas.

**Tensions:** The paper claims SFT-auto breaks the text-structure trade-off, but the theoretical basis for why the multi-task LLM training achieves what noise injection and similarity filtering cannot is not provided. The empirical gap is demonstrated, but the mechanism remains unclear.

**Key open question:** Is the text-structure trade-off a fundamental architectural property (LLMs cannot simultaneously exploit structural and textual signals at equal quality) or is it a training data distribution issue that sufficiently diverse multi-task training can overcome? The paper demonstrates the latter empirically but does not rule out the former theoretically.

---

## Literature Gap Report

- **Mujkanovic et al. (2022)** "Are Defenses for GNNs Robust?" NeurIPS 2022 — cited as the basis for the PGD-Guard adaptive attack, which is correct. But this paper's main finding (that many claimed defenses fail when re-evaluated under consistent conditions) is directly relevant to the paper's motivation and warrants more prominent treatment.
- **Gosch et al. (2023)** "Adversarial Training for Graph Neural Networks: Pitfalls, Solutions, and New Directions" NeurIPS 2023 — cited, but its finding that poisoning attacks pair naturally with transductive settings is treated as a given without acknowledgment that it comes from this paper.
- No obvious missing recent top-venue papers on TAG robustness identified; the field is young and most relevant work is concurrent preprints.

---

## Open Questions

1. The cosine similarity threshold of 0.5 in SFT-auto's structure attack detection is a hardcoded hyperparameter. How sensitive is performance to this threshold, and can it be learned or calibrated during training?

2. The detection rate figures in Figure 6b show 6.2–17.4× improvements over AutoGCN, but only relative ratios are given. What are the absolute detection rates? If AutoGCN achieves 5% detection and SFT-auto achieves 31–87%, the story differs from both achieving >90%.

3. The paper uses GPT-4o-mini for text attacks. Would weaker open-source models produce qualitatively different results? This matters for the ecological validity of the attack.

4. SFT-auto training uses r = min(1/|C|, 0.15) as the attack ratio. Since the test perturbation budget is 40% for evasion and 80% for poisoning — far above 15% — why does this mismatch not hurt SFT-auto's detection?

5. The simultaneous (hybrid) attack results are in Appendix E. Do any methods maintain acceptable performance under hybrid attacks, or does the trade-off simply remain unsolved in that setting?
