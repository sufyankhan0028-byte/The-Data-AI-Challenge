# Hackathon Interview Prep Guide

This document synthesizes the entire architecture and engineering philosophy into quick, high-impact talking points for presenting to the judges.

## Core Value Proposition
**"We built a fully localized, CPU-optimized Talent Intelligence Engine that processes 100,000 highly-nested candidate profiles in under 5 minutes without a single external API call."**

## Technical Pillars to Highlight

### 1. Dual-Encoder Retrieval (The Funnel)
- **What it is**: A custom `BM25Okapi` sparse index merged with an `all-MiniLM-L6-v2` dense semantic space.
- **Why it matters**: It prevents the classic semantic search failure where exact keywords (e.g. `TensorRT`) get lost in semantic fuzziness. The hybrid 0.4 / 0.6 weighting guarantees we capture both hard skills and semantic trajectory.

### 2. Multi-Dimensional Feature Engineering (The Bridge)
- **What it is**: We aggressively flattened the JSON into 70 distinct vectors utilizing `pyarrow` backed `Parquet` serialization.
- **Why it matters**: We didn't just count skills; we built temporal heuristics. We explicitly calculate **promotions** by computationally mapping identical companies across changing titles over time.

### 3. LightGBM Learning-to-Rank (The Brain)
- **What it is**: `lgb.LGBMRanker` using the `lambdarank` objective function.
- **Why it matters**: Rather than slapping an arbitrary linear weighting formula (e.g. `Score = 0.5*YoE + 0.5*Skills`), the tree-based model mathematically learns the non-linear interactions. It inherently learns that "High YoE + Zero Vector Database Skills" is a massive negative signal for this specific role.

### 4. V2 Honeypot Fraud Detection (The Firewall)
- **What it is**: A rigid heuristic engine merged with unsupervised ML clustering (`Isolation Forests`).
- **Why it matters**: The dataset was boobytrapped. Our pipeline automatically catches chronological impossibilities (e.g. claiming 5 years of `langchain`, which released in 2022) and bot-like behavioral signatures (100% response rates paired with thousands of views).

### 5. Explainable AI (The Trust Layer)
- **What it is**: Deterministic natural language generation mapped directly to explicit features.
- **Why it matters**: Recruiters will not blindly trust a black box. Our `ExplanationGenerator` outputs hallucination-free, 1-2 sentence summaries mathematically grounded by SHAP (`TreeExplainer`) feature contributions.

## Anticipating Judge Questions

**Q: Why didn't you use a Vector Database like Pinecone or Chroma?**
> A: "Network I/O. The constraint was processing 100k records at maximum velocity. Spinning up a localized dense `numpy` matrix alongside a serialized BM25 object allowed us to execute similarity functions entirely in memory, sidestepping REST API latency completely."

**Q: How do you handle missing data in the raw JSON?**
> A: "We utilize safe `.get(key, default)` extraction loops at the very edge of the pipeline. If a candidate is completely missing a career history array, the Feature Engine defaults their Average Tenure to 0.0 rather than throwing a KeyError, ensuring the pipeline never crashes mid-execution."

**Q: Why LightGBM instead of a Deep Learning ranker?**
> A: "Speed and explainability. LightGBM trains in a matter of seconds on standard CPU cores and natively supports SHAP TreeExplainers out of the box, allowing us to perfectly isolate and visualize feature importance for the UI."
