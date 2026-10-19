from django.test import SimpleTestCase

from .ai import _normalize_application, fallback_application, _resume_skills
from .models import Job


class GroundedAssistantTests(SimpleTestCase):
    def setUp(self):
        self.job = Job(
            title='Backend Engineer', company='Example Co', location='Remote',
            experience='0-2 years', description='Build APIs with Django and Python.',
            required_skills=['Python', 'Django', 'Kubernetes'], preferred_skills=[]
        )
        self.resume = 'Built Python APIs with Django for an internal analytics tool.'

    def test_skill_recommendations_do_not_match_substrings(self):
        job = Job(required_skills=['Java'], preferred_skills=[])
        present, missing = _resume_skills('Built JavaScript interfaces.', job)
        self.assertEqual(present, [])
        self.assertEqual(missing, ['Java'])

    def test_fallback_output_is_structured_and_editable(self):
        output = fallback_application(self.resume, self.job)
        self.assertTrue(output['structured_output']['grounding']['validated'])
        self.assertTrue(output['structured_output']['cover_letter']['editable'])
        self.assertEqual(len(output['interview_qa']), 8)

    def test_model_output_with_unverified_claims_is_rejected(self):
        unsafe = {
            'resume_suggestions': [{'text': 'Highlight Kubernetes leadership.', 'evidence': ['Kubernetes leadership']}],
            'cover_letter': {'text': 'I led a Kubernetes migration.', 'evidence': ['Kubernetes migration']},
            'interview_qa': [{'question': 'Tell me about Kubernetes.', 'answer': 'I led the migration.', 'evidence': ['Kubernetes migration']}],
            'unsupported_claims': [],
        }
        self.assertIsNone(_normalize_application(unsafe, self.resume, self.job))
