# System Architecture

## 1. High-Level Architecture
The Redrob Talent Intelligence Engine is a hyper-optimized, multi-stage retrieval and ranking pipeline designed to process 100,000 highly nested candidate profiles in under 5 minutes on a local CPU. The architecture strictly avoids external API calls (no OpenAI, no external Vector DBs), utilizing local in-memory embeddings and sparse BM25 indices.

The system is split into two primary layers:
1. **The Python ML Backend**: A FastAPI monolith containing the `FinalRankingService`, which orchestrates the pipeline from candidate loading to LightGBM inference.
2. **The Next.js Glassmorphism Dashboard**: A rich React frontend that visualizes the candidate analytics, explainability metrics, and dataset forensics.

## 2. Hybrid Retrieval Pipeline
To narrow down 100,000 candidates to a viable candidate pool, we utilize a dual-encoder `HybridRetrievalService`:
- **Sparse BM25 (Lexical)**: Utilizes a custom `BM25Okapi` implementation that tokenizes the candidate's career history, explicit skills, and summary. This captures exact keyword matches (e.g., `TensorRT`, `Kubernetes`).
- **Dense Cosine (Semantic)**: Utilizes a local `SentenceTransformer` (`all-MiniLM-L6-v2`) to encode the unstructured text. It calculates rapid Cosine Similarity against the parsed Job Description to capture semantic meaning (e.g., matching "Data Scientist" to "Machine Learning Engineer").
- **Ensemble Merge**: The final retrieval score is a weighted combination (0.4 BM25 + 0.6 Dense) to generate the Top 1,000 candidate pool for downstream processing.

## 3. Feature Engineering
The `FeatureEngineeringService` takes the retrieved candidates and flattens their deeply nested JSON graphs into a sprawling 70-dimension feature vector. 
Key heuristic groups include:
- **Semantic Overlap**: Direct vector distances.
- **Career Metrics**: Computes average tenure, explicit promotion counts (by tracking identical company IDs with title changes over time), and startup experience.
- **Deep Skill Bins**: Boolean flags for Vector Databases (Pinecone, Milvus), Retrieval (RAG), and LLM Fine-Tuning (LoRA, PEFT).
- **Behavioral Footprint**: Inherits Redrob proprietary signals like recruiter response rates and GitHub activity.

## 4. Learning to Rank (LTR)
We bypass simple linear weights by deploying a highly nonlinear **LightGBM Ranker**.
- **Objective**: `lambdarank` optimized to maximize `NDCG@10`.
- **Training**: We generated pseudo-labels (`3=Excellent` to `0=Bad`) based on strict multi-dimensional heuristics. The model learns how different features interact (e.g., high YoE + high vector DB skills = massive boost, but high YoE + zero Python = massive penalty).
- **Inference**: The model consumes the 70D feature vectors of the Top 1,000 candidates and outputs the final probabilistic scores to isolate the Top 100.

## 5. Honeypot & Fraud Detection (V2)
The hackathon dataset was seeded with synthetic traps. The `HoneypotDetectorV2` acts as a multi-stage firewall:
- **Timeline Impossibilities**: Penalizes candidates claiming 5 years of `langchain` experience (which only released in 2022).
- **Contradictions**: Flags frontend titles explicitly claiming ML engineer summaries.
- **Bot Behavior**: Isolates identical signature footprints (e.g., 100% response rates paired with thousands of views and 80+ distinct skills).
- **Unsupervised ML Backups**: Utilizes `Isolation Forests` and `DBSCAN` density clustering in our offline notebooks to mathematically rip out multi-dimensional anomalies that evade heuristic rules.

## 6. Explainability
Because recruiters require trust in the AI, the `ExplanationGenerator` outputs hallucination-free, deterministic textual summaries for every candidate.
- It dynamically converts the `FeatureVector` back into natural language (e.g., "7.4 years of experience building production retrieval systems with strong Python").
- It explicitly extracts the Top 3 numerical features driving the LightGBM score.
- We utilize `SHAP` (Shapley Additive Explanations) via `TreeExplainer` during offline training to calculate the exact global feature importance of the entire model.
