# Design Decisions & Tradeoffs

## 7. Tradeoffs & Architectural Constraints
The core constraint of this challenge was that the solution must run entirely locally on a single machine utilizing only CPUs, with strict prohibitions on external APIs (like OpenAI) or massive Vector Databases (like Pinecone).

1. **In-Memory Retrieval vs Real Database**: 
   - *Decision*: We utilized localized `numpy` operations and `SentenceTransformers` natively in memory instead of spinning up an Elasticsearch or ChromaDB Docker container.
   - *Tradeoff*: Massive speed enhancements and zero infrastructure complexity, at the cost of being unable to scale to 10+ million rows without eventually hitting RAM ceilings.
2. **LightGBM vs Deep Learning**:
   - *Decision*: We utilized LightGBM instead of a Deep Neural Network (DNN) for the ranking stage.
   - *Tradeoff*: LightGBM trains in seconds on CPUs and offers native `TreeExplainer` SHAP explainability. While a DNN might theoretically capture more complex embeddings interactions, it would fail the sub-5-minute execution constraint on a CPU environment.
3. **Heuristic Fraud Detection vs LLM Detection**:
   - *Decision*: We built rigid, hard-coded heuristics (e.g., checking release dates of open source packages) for the Honeypot Detector.
   - *Tradeoff*: Hard-coded heuristics require manual upkeep of tech stacks and dates, but they execute in microseconds compared to a local LLM prompt evaluation which would take hours to process 100,000 JSON blobs on CPU.

## 8. Failure Cases & Vulnerabilities
1. **Semantic Drift**: Because we use `all-MiniLM-L6-v2`, the embedding dimension is only 384. Highly nuanced AI skills (e.g., distinguishing between `PEFT` and `QLoRA`) might map to identical vectors due to the small embedding space, causing the model to treat distinct skills identically.
2. **Missing Metadata Resiliency**: The `FeatureEngineeringService` handles missing arrays gracefully via `get("skills", [])`, but if the entire JSON schema radically shifts format in production, the static extraction layers will crash.
3. **Keyword Stuffing Evasion**: While we penalize claiming 100+ skills, a sophisticated synthetic profile could claim exactly 45 perfectly curated, highly relevant skills across exact required clusters. The heuristic engines would struggle to flag this, which is why the downstream unsupervised `Isolation Forests` in the forensics notebooks are required as backup.

## 9. Future Improvements
1. **Dynamic Embedding Quantization**: We could apply ONNX runtime or INT8 quantization to the local SentenceTransformer, allowing us to upgrade to a massive 1024-dimension embedding model (like `bge-large`) without suffering CPU latency penalties.
2. **Graph Neural Networks (GNN)**: Currently, promotions are tracked via a simple linear loop. We could model the candidate pool as a Graph (Nodes = Candidates/Companies, Edges = Work History) to mathematically identify prestige networks or hidden talent clusters based on alumni graphs.
3. **Continuous Active Learning (CAL)**: We could wire the `POST /api/label` endpoint directly into an automated nightly LightGBM retraining loop. As recruiters click "Approve" or "Reject" on the Next.js dashboard, the model's weights would dynamically shift the next morning.
