from django.test import TestCase
from django.urls import reverse

from tracker.models import Comment, Project, Task

from .factories import PASSWORD, make_project, make_task, make_user


class ViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = make_user("boss", manager=True)
        cls.alice = make_user("alice")
        cls.project = make_project(cls.manager, [cls.alice])
        cls.task = make_task(cls.project, cls.manager, cls.alice, "Сделать API")

    def login(self, user):
        self.client.login(username=user.username, password=PASSWORD)

    def test_login_required(self):
        resp = self.client.get(reverse("tracker:task_list"))
        self.assertRedirects(resp, "/accounts/login/?next=/tasks/")

    def test_signup_and_login(self):
        resp = self.client.post(
            reverse("signup"),
            {
                "username": "newbie",
                "email": "n@test.local",
                "password1": "Very-strong-1",
                "password2": "Very-strong-1",
            },
        )
        self.assertRedirects(resp, reverse("tracker:task_list"))
        resp = self.client.get(reverse("tracker:task_list"))
        self.assertContains(resp, "newbie")

    def test_task_list_and_filter(self):
        self.login(self.alice)
        make_task(self.project, self.alice, self.alice, "Готовая", status=Task.Status.DONE)
        resp = self.client.get(reverse("tracker:task_list"))
        self.assertContains(resp, "Сделать API")
        self.assertContains(resp, "Готовая")
        resp = self.client.get(reverse("tracker:task_list"), {"status": "done"})
        self.assertNotContains(resp, "Сделать API")
        self.assertContains(resp, "Готовая")
        resp = self.client.get(reverse("tracker:task_list"), {"project": self.project.pk, "mine": 1})
        self.assertEqual(resp.status_code, 200)

    def test_task_detail(self):
        self.login(self.alice)
        resp = self.client.get(self.task.get_absolute_url())
        self.assertContains(resp, "Сделать API")

    def test_create_task_assigns_to_self(self):
        self.login(self.alice)
        resp = self.client.post(
            reverse("tracker:task_create"),
            {
                "project": self.project.pk,
                "title": "Новая",
                "status": "todo",
                "priority": 2,
                "assignee": self.alice.pk,
            },
        )
        task = Task.objects.get(title="Новая")
        self.assertRedirects(resp, task.get_absolute_url())
        self.assertEqual(task.author, self.alice)
        self.assertEqual(task.assignee, self.alice)

    def test_create_form_get(self):
        self.login(self.alice)
        resp = self.client.get(reverse("tracker:task_create"), {"project": self.project.pk})
        self.assertEqual(resp.status_code, 200)

    def test_update_task(self):
        self.login(self.alice)
        resp = self.client.post(
            reverse("tracker:task_update", args=[self.task.pk]),
            {
                "project": self.project.pk,
                "title": "API v2",
                "status": "in_progress",
                "priority": 3,
                "assignee": self.alice.pk,
            },
        )
        self.assertRedirects(resp, self.task.get_absolute_url())
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, "API v2")

    def test_status_change(self):
        self.login(self.alice)
        self.client.post(reverse("tracker:task_status", args=[self.task.pk]), {"status": "done"})
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, Task.Status.DONE)

    def test_status_get_not_allowed(self):
        self.login(self.alice)
        resp = self.client.get(reverse("tracker:task_status", args=[self.task.pk]))
        self.assertEqual(resp.status_code, 405)

    def test_comment(self):
        self.login(self.alice)
        self.client.post(reverse("tracker:task_comment", args=[self.task.pk]), {"text": "Готово к ревью"})
        self.assertTrue(Comment.objects.filter(task=self.task, author=self.alice).exists())

    def test_author_can_delete(self):
        own = make_task(self.project, self.alice, self.alice, "Моя")
        self.login(self.alice)
        resp = self.client.post(reverse("tracker:task_delete", args=[own.pk]))
        self.assertRedirects(resp, reverse("tracker:task_list"))
        self.assertFalse(Task.objects.filter(pk=own.pk).exists())

    def test_project_pages(self):
        self.login(self.alice)
        resp = self.client.get(reverse("tracker:project_list"))
        self.assertContains(resp, self.project.name)
        resp = self.client.get(self.project.get_absolute_url())
        self.assertContains(resp, "Сделать API")

    def test_manager_creates_project(self):
        self.login(self.manager)
        resp = self.client.post(reverse("tracker:project_create"), {"name": "Новый", "members": [self.alice.pk]})
        project = Project.objects.get(name="Новый")
        self.assertRedirects(resp, project.get_absolute_url())
        self.assertEqual(project.owner, self.manager)

    def test_manager_updates_and_deletes_project(self):
        self.login(self.manager)
        self.client.post(reverse("tracker:project_update", args=[self.project.pk]), {"name": "Переименован"})
        self.project.refresh_from_db()
        self.assertEqual(self.project.name, "Переименован")
        self.client.post(reverse("tracker:project_delete", args=[self.project.pk]))
        self.assertFalse(Project.objects.filter(pk=self.project.pk).exists())
