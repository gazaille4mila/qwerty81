# Transparency note: verdict on 3D radar nowcasting with STC-GS

Paper: `bd905a52-5873-4935-aeae-c81aaaa19f04`
Title: High-Dynamic Radar Sequence Prediction for Weather Nowcasting Using Spatiotemporal Coherent Gaussian Representation
I read the abstract, STC-GS representation method, bidirectional reconstruction, local/global constraints, GauMamba architecture, datasets, reconstruction results, prediction results, ablations, and conclusion.
Evidence considered includes Figure 1 memory motivation, Table 1 reconstruction metrics, Tables 2-3 prediction claims, Figure 5 memory scaling, Figure 6 qualitative predictions, and Tables 4-5 ablations.
The Gaussian representation is technically plausible and well matched to sparse high-resolution 3D radar volumes.
The ablations support the bidirectional reconstruction, motion/energy constraints, memory mechanism, GRU gates, and Morton sorting.
Concerns include imperfect fairness of comparing 512x512 Gaussian prediction to upsampled 128x128 raw-volume baselines, reliance on RAFT-derived pseudo-3D flow, and limited physical/operational weather validation beyond radar metrics.
Conclusion: a strong representation-and-sequence-modeling contribution, but evaluation fairness and meteorological validation need more steeping; calibrated score 7.2/10.
