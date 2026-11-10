"""Проверки на IDOR и разграничение прав: чужие объекты по прямому id недоступны."""

from django.test import TestCase
from django.urls import reverse

from tracker.models import Comment, Project, Task

from .factories import PASSWORD, make_project, make_task, make_user


class IdorTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = make_user("boss", manager=True)
        cls.alice = make_user("alice")
        cls.bob = make_user("bob")
        cls.project = make_project(cls.manager, [cls.alice, cls.bob])
        cls.secret_project = make_project(cls.manager, [cls.bob], name="Секретный")
        cls.bob_task = make_task(cls.project, cls.manager, cls.bob, "Задача Боба")

    def setUp(self):
        self.client.login(username="alice", password=PASSWORD)

    def test_foreign_task_detail_404(self):
        resp = self.client.get(reverse("tracker:task_detail", args=[self.bob_task.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_foreign_task_edit_404(self):
        url = reverse("tracker:task_update", args=[self.bob_task.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        resp = self.client.post(url, {"project": self.project.pk, "title": "взлом", "status": "done", "priority": 1})
        self.assertEqual(resp.status_code, 404)
        self.bob_task.refresh_from_db()
        self.assertEqual(self.bob_task.title, "Задача Боба")

    def test_foreign_task_delete_404(self):
        resp = self.client.post(reverse("tracker:task_delete", args=[self.bob_task.pk]))
        self.assertEqual(resp.status_code, 404)
        self.assertTrue(Task.objects.filter(pk=self.bob_task.pk).exists())

    def test_foreign_task_status_and_comment_404(self):
        resp = self.client.post(reverse("tracker:task_status", args=[self.bob_task.pk]), {"status": "done"})
        self.assertEqual(resp.status_code, 404)
        resp = self.client.post(reverse("tracker:task_comment", args=[self.bob_task.pk]), {"text": "hi"})
        self.assertEqual(resp.status_code, 404)
        self.assertFalse(Comment.objects.exists())

    def test_assignee_cannot_delete_task_created_by_manager(self):
        task = make_task(self.project, self.manager, self.alice, "Назначена Алисе")
        resp = self.client.post(reverse("tracker:task_delete", args=[task.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_foreign_project_404(self):
        resp = self.client.get(reverse("tracker:project_detail", args=[self.secret_project.pk]))
        self.assertEqual(resp.status_code, 404)

    def test_task_list_does_not_leak(self):
        resp = self.client.get(reverse("tracker:task_list"))
        self.assertNotContains(resp, "Задача Боба")

    def test_cannot_create_task_in_foreign_project(self):
        self.client.post(
            reverse("tracker:task_create"),
            {
                "project": self.secret_project.pk,
                "title": "внедрение",
                "status": "todo",
                "priority": 2,
            },
        )
        self.assertFalse(Task.objects.filter(title="внедрение").exists())

    def test_regular_user_cannot_manage_projects(self):
        self.assertEqual(self.client.get(reverse("tracker:project_create")).status_code, 403)
        resp = self.client.post(reverse("tracker:project_update", args=[self.project.pk]), {"name": "x"})
        self.assertEqual(resp.status_code, 403)
        resp = self.client.post(reverse("tracker:project_delete", args=[self.project.pk]))
        self.assertEqual(resp.status_code, 403)
        self.assertTrue(Project.objects.filter(pk=self.project.pk).exists())

    def test_manager_sees_everything(self):
        self.client.logout()
        self.client.login(username="boss", password=PASSWORD)
        resp = self.client.get(reverse("tracker:task_detail", args=[self.bob_task.pk]))
        self.assertEqual(resp.status_code, 200)
