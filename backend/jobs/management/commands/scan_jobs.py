from django.core.management.base import BaseCommand
from jobs.services import scan_jobs
class Command(BaseCommand):
    help='Scan configured job sources'
    def handle(self,*args,**kwargs):
        jobs=scan_jobs(); self.stdout.write(self.style.SUCCESS(f'Scanned {len(jobs)} jobs'))
