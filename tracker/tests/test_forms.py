import datetime

from django.test import TestCase
from django.utils import timezone

from accounts.forms import SignUpForm
from tracker.forms import TaskForm

from .factories import make_project, make_user


class TaskFormTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = make_user("boss", manager=True)
        cls.alice = make_user("alice")
        cls.outsider = make_user("eve")
        cls.project = make_project(cls.manager, [cls.alice])
        cls.other_project = make_project(cls.manager, [], name="Чужой")

    def data(self, **kw):
        d = {
            "project": self.project.pk,
            "title": "Тест",
            "status": "todo",
            "priority": 2,
            "assignee": self.alice.pk,
            "due_date": "",
        }
        d.update(kw)
        return d

    def test_valid(self):
        form = TaskForm(self.data(), user=self.alice)
        self.assertTrue(form.is_valid(), form.errors)

    def test_past_due_date(self):
        yesterday = timezone.localdate() - datetime.timedelta(days=1)
        form = TaskForm(self.data(due_date=yesterday), user=self.alice)
        self.assertFalse(form.is_valid())
        self.assertIn("due_date", form.errors)

    def test_user_cannot_pick_foreign_project(self):
        form = TaskForm(self.data(project=self.other_project.pk), user=self.alice)
        self.assertFalse(form.is_valid())
        self.assertIn("project", form.errors)

    def test_user_cannot_assign_other_user(self):
        form = TaskForm(self.data(assignee=self.manager.pk), user=self.alice)
        self.assertFalse(form.is_valid())
        self.assertIn("assignee", form.errors)

    def test_manager_cannot_assign_non_member(self):
        form = TaskForm(self.data(assignee=self.outsider.pk), user=self.manager)
        self.assertFalse(form.is_valid())
        self.assertIn("assignee", form.errors)

    def test_empty_title(self):
        form = TaskForm(self.data(title=""), user=self.alice)
        self.assertFalse(form.is_valid())


class SignUpFormTests(TestCase):
    def test_duplicate_email(self):
        make_user("alice")
        form = SignUpForm(
            {"username": "new", "email": "ALICE@test.local", "password1": "Very-strong-1", "password2": "Very-strong-1"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("email", form.errors)
