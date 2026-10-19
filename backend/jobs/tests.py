"""
Django Unit Tests for Intelligent Job Matching & IR Ranking Engine.
"""

from django.test import TestCase
from jobs.matching_engine import (
    calculate_intelligent_match,
    compare_skills_semantically,
    canonicalize_skill,
    extract_skills_from_text,
    parse_candidate_years,
    parse_job_experience_range,
    determine_seniority,
    SemanticEmbeddingEngine
)
from evaluation.benchmark_matching import MatchingBenchmarkRunner


class IntelligentMatchingTestCase(TestCase):
    def test_canonicalization(self):
        self.assertEqual(canonicalize_skill('PostgreSQL'), 'postgresql')
        self.assertEqual(canonicalize_skill('postgres'), 'postgresql')
        self.assertEqual(canonicalize_skill('k8s'), 'kubernetes')
        self.assertEqual(canonicalize_skill('py'), 'python')
        self.assertEqual(canonicalize_skill('js'), 'javascript')

    def test_semantic_equivalences(self):
        # FastAPI satisfies Django
        eval_res = compare_skills_semantically(['FastAPI', 'Python'], ['Django', 'Python'])
        matched = [m['canonical'] for m in eval_res['exact_matches'] + eval_res['semantic_matches']]
        self.assertIn('django', matched)

        # Postgres satisfies SQL
        eval_res2 = compare_skills_semantically(['PostgreSQL'], ['SQL'])
        matched2 = [m['canonical'] for m in eval_res2['exact_matches'] + eval_res2['semantic_matches']]
        self.assertIn('sql', matched2)

    def test_domain_gating_prevents_false_matches(self):
        # Java does NOT match JavaScript
        eval_res = compare_skills_semantically(['JavaScript'], ['Java'])
        matched = [m['canonical'] for m in eval_res['exact_matches'] + eval_res['semantic_matches']]
        self.assertNotIn('java', matched)

        # Rust does NOT match REST APIs
        eval_res2 = compare_skills_semantically(['Rust'], ['REST APIs'])
        matched2 = [m['canonical'] for m in eval_res2['exact_matches'] + eval_res2['semantic_matches']]
        self.assertNotIn('rest apis', matched2)

    def test_embedding_engine(self):
        engine = SemanticEmbeddingEngine.get_instance()
        text_a = "Senior Python engineer building microservices with FastAPI and Docker."
        text_b = "Python backend developer working with Docker containers and REST APIs."
        text_c = "Experienced chef specializing in Italian pastry and bread baking."
        sim_related = engine.compute_similarity(text_a, text_b)
        sim_unrelated = engine.compute_similarity(text_a, text_c)
        self.assertGreater(sim_related, sim_unrelated)

    def test_ir_benchmark_ndcg(self):
        runner = MatchingBenchmarkRunner()
        results = runner.run_full_benchmark()
        macro = results['macro_metrics']
        self.assertGreaterEqual(macro['ndcg@3'], 0.85, f"NDCG@3 should exceed 0.85, got {macro['ndcg@3']}")
        self.assertEqual(macro['p@1'], 1.0, f"Precision@1 should be 1.0, got {macro['p@1']}")
        self.assertEqual(macro['mrr'], 1.0, f"MRR should be 1.0, got {macro['mrr']}")
