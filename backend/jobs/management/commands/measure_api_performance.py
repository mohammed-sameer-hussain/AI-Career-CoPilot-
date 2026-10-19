import json
import time

from django.core.management.base import BaseCommand
from django.test import Client
from django.test.utils import override_settings


class Command(BaseCommand):
    help = 'Measure local API response latency for representative read endpoints.'

    def add_arguments(self, parser):
        parser.add_argument('--runs', type=int, default=20)

    def handle(self, *args, **options):
        runs = max(3, options['runs'])
        client = Client()
        endpoints = ['/api/jobs/?limit=20', '/api/jobs/?limit=20&search=python']
        measurements = {}
        with override_settings(ALLOWED_HOSTS=['testserver', '127.0.0.1', 'localhost']):
            for endpoint in endpoints:
                samples = []
                statuses = []
                for _ in range(runs):
                    started = time.perf_counter()
                    response = client.get(endpoint)
                    samples.append((time.perf_counter() - started) * 1000)
                    statuses.append(response.status_code)
                samples.sort()
                measurements[endpoint] = {
                    'status_codes': sorted(set(statuses)),
                    'runs': runs,
                    'p50_ms': round(samples[len(samples) // 2], 2),
                    'p95_ms': round(samples[min(len(samples) - 1, int(len(samples) * 0.95))], 2),
                    'max_ms': round(samples[-1], 2),
                }
        self.stdout.write(json.dumps(measurements, indent=2))
