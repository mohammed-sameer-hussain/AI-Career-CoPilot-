from django.core.management.base import BaseCommand
from evaluation.benchmark_matching import MatchingBenchmarkRunner, format_benchmark_report

class Command(BaseCommand):
    help = 'Runs the Intelligent Job Matching IR Evaluation Benchmark Suite'

    def handle(self, *args, **options):
        self.stdout.write("Running Intelligent Job Matching IR Benchmark...")
        runner = MatchingBenchmarkRunner()
        results = runner.run_full_benchmark()
        report = format_benchmark_report(results)
        self.stdout.write(report)
        macro = results['macro_metrics']
        if macro['ndcg@3'] >= 0.85:
            self.stdout.write(self.style.SUCCESS(f"Evaluation PASSED! Mean NDCG@3: {macro['ndcg@3']:.4f}"))
        else:
            self.stdout.write(self.style.WARNING(f"Evaluation warning: NDCG@3 is {macro['ndcg@3']:.4f}"))

