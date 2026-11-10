from io import StringIO

from django.core.management import call_command
from django.test import TestCase

from tracker.models import Project, Task


class SeedDemoTests(TestCase):
    def test_seed_is_idempotent(self):
        call_command("seed_demo", stdout=StringIO())
        call_command("seed_demo", stdout=StringIO())
        self.assertEqual(Project.objects.count(), 2)
        self.assertEqual(Task.objects.count(), 6)
