from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from .auth import make_tokens
from .models import CandidateProfile


class SecurityRegressionTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.profile = CandidateProfile.objects.create(
            name="Test Candidate", email="test@example.com", password=""
        )

    def auth(self):
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {make_tokens(self.profile)['access']}")

    def test_access_token_is_jwt_and_refresh_token_cannot_authenticate(self):
        tokens = make_tokens(self.profile)
        self.assertEqual(len(tokens["access"].split(".")), 3)
        self.client.credentials(HTTP_AUTHORIZATION=f"Bearer {tokens['refresh']}")
        response = self.client.get("/api/profiles/")
        self.assertEqual(response.status_code, 401)

    def test_resume_rejects_invalid_file_signature(self):
        self.auth()
        upload = SimpleUploadedFile("resume.pdf", b"not a PDF", content_type="application/pdf")
        response = self.client.post("/api/resumes/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 400)

    def test_resume_rejects_unsupported_extension(self):
        self.auth()
        upload = SimpleUploadedFile("resume.exe", b"MZ", content_type="application/octet-stream")
        response = self.client.post("/api/resumes/", {"file": upload}, format="multipart")
        self.assertEqual(response.status_code, 400)
