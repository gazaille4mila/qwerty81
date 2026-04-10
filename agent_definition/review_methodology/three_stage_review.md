## Review Methodology: Three-Stage Review

A three-phase process for producing thorough, well-informed paper reviews.

```
Paper  →  Phase 1: Reading & Orientation  →  Phase 2: Research  →  Phase 3: Findings & Review
```

---

### Phase 1: Reading & Orientation

Read the full paper. Identify:
- The core research question
- The proposed method or contribution
- The evaluation approach

Check existing reviews and comments on the paper. Note which aspects have already been covered and where gaps remain. Check the profiles of the submitter and commenters to understand their expertise.

Produce a **Contribution Map** — decompose the paper into 3-5 distinct contribution areas, each with:
- A concise label (e.g. "challenge dataset construction")
- A description of what the paper claims in this area
- A weight reflecting centrality to the paper (0.0-1.0, must sum to 1.0)

Use this map to focus your effort on the areas that matter most, evaluated through the lens of your role.

---

### Phase 2: Research

For each contribution area relevant to your role, build the background knowledge you need to evaluate it properly. Independent areas can be researched in parallel.

What "research" means depends on your evaluation role. Examples:
- Surveying prior approaches and competing methods
- Understanding the technical details of a specific technique
- Investigating reproducibility norms for the domain
- Checking ethical precedents or known harms in the application area

**If Paper Lantern tools are available, prefer them for this phase when they fit your evaluation lens:**
- `explore_approaches` — for surveying prior approach families in a problem area
- `deep_dive` — for investigating a specific technique's mechanism and evidence gaps
- `compare_approaches` — for competitive comparison against alternatives
- `check_feasibility` — for assessing practical viability, risks, and failure modes

Not every role benefits equally from these tools. Use them where they fit, skip them where they don't.

The output for each area is a **Brief** — a short summary of what you learned that is relevant to your evaluation. This is your working notes, not part of the final review.

---

### Phase 3: Findings & Review

#### Step A: Per-Area Findings

For each contribution area, produce a findings report grounded in the paper and your research from Phase 2. Apply your role's evaluation criteria to each area. Independent areas can run in parallel.

Every finding must reference specifics — paper sections, tables, figures, or external evidence from Phase 2. No vague assessments.

#### Step B: Synthesis

Collect all per-area findings and identify:
- **Cross-cutting themes** — issues or strengths that appear across multiple areas
- **Tensions** — areas where one contribution's strength undermines another's claims
- **The key open question** — the single most important thing that your evaluation could not resolve

#### Step C: Assemble Final Review

Combine the per-area findings and synthesis into your review. The specific sections this methodology contributes are described below.

---

## Methodology-Specific Subsections

Also include the following sections in your final review:

```
### Per-Area Findings

One sub-subsection for each contribution area identified in Phase 1's Contribution Map.
Label each with the area's concise name. Within each area, present the findings report
produced in Phase 3A.

### Synthesis

- Cross-cutting themes — issues or strengths that appeared across multiple areas
- Tensions — areas where one contribution's strength undermines another's claims
- Key open question — the single most important thing your evaluation could not resolve
```
