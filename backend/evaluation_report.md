# Intelligent Job Matching Evaluation Report

```
================================================================================
     AI CAREER COPILOT - INTELLIGENT JOB MATCHING EVALUATION BENCHMARK
================================================================================

1. MACRO INFORMATION RETRIEVAL (IR) RANKING METRICS:
--------------------------------------------------------------------------------
  * Mean NDCG@1:      1.0000  (Ranking accuracy at top position)
  * Mean NDCG@3:      0.9461  (Ranking accuracy across top-3 positions)
  * Mean NDCG@5:      0.9553  (Ranking accuracy across top-5 positions)
  * Mean Reciprocal Rank (MRR):  1.0000  (Inverse rank of first relevant match)
  * Precision@1:      1.0000  (Fraction of #1 results that are relevant)
  * Precision@3:      0.6111  (Fraction of top-3 results that are relevant)
  * Mean Average Precision (MAP): 0.9583

2. PER-CANDIDATE RANKING PERFORMANCE:
--------------------------------------------------------------------------------
Candidate Profile                      | Top Recommended Job          | Score  | NDCG@3  | MRR  
--------------------------------------------------------------------------------
Candidate A (Senior Python / Cloud A   | Senior Python Backend Arch   | 88.3   | 1.0000  | 1.00 
Candidate B (Junior React Frontend D   | Junior Frontend Engineer (   | 85.2   | 1.0000  | 1.00 
Candidate C (Cloud DevOps / Infrastr   | Senior DevOps & Cloud Plat   | 95.5   | 0.9468  | 1.00 
Candidate D (Staff AI & NLP Scientis   | Staff Machine Learning / A   | 89.4   | 1.0000  | 1.00 
Candidate E (Enterprise Java Backend   | Enterprise Java Backend De   | 89.1   | 0.8124  | 1.00 
Candidate F (Customer Support Specia   | Customer Support & Operati   | 80.0   | 0.9173  | 1.00 

3. SEMANTIC EQUIVALENCE & ONTOLOGY VERIFICATION:
--------------------------------------------------------------------------------
  Success Rate: 6/6 (100.0%)
  [PASS] PostgreSQL satisfies SQL requirement
  [PASS] FastAPI satisfies Django backend requirement
  [PASS] Docker satisfies Containerization / Kubernetes ecosystem
  [PASS] ReactJS canonical alias resolution
  [PASS] Domain Isolation: Java does NOT match JavaScript
  [PASS] Domain Isolation: Rust does NOT match REST APIs

4. MATCH SCORE VS. HIRING PROBABILITY DIVERGENCE ANALYSIS:
--------------------------------------------------------------------------------
  * Scenario: High Selectivity Top MNC (DeepMind/Google)
    Candidate: Candidate A (Senior Python / Cloud Architect) -> Job: Staff Machine Learning / AI Research Engineer
    Match Score: 52.0%  vs.  Hiring Probability: 3.0% (Delta: 49.0%)
    Rationale: Applicant volume and extreme selectivity significantly discount hire odds despite high skill.

  * Scenario: Overqualification / Senior applying to Fresher QA
    Candidate: Candidate A (Senior Python / Cloud Architect) -> Job: Entry-Level Python QA & Automation Tester
    Match Score: 45.3%  vs.  Hiring Probability: 3.0% (Delta: 42.3%)
    Rationale: Overqualification penalty suppresses hire odds due to flight-risk / attrition expectations.

  * Scenario: Missing Critical Core Gating Skills (React Jr to Enterprise Java)
    Candidate: Candidate B (Junior React Frontend Developer) -> Job: Enterprise Java Backend Developer
    Match Score: 41.7%  vs.  Hiring Probability: 3.0% (Delta: 38.7%)
    Rationale: Zero core language alignment triggers gating penalties, pushing hire odds to floor.

================================================================================
```
