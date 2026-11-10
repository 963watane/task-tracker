from django.urls import reverse
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.test import APITestCase

from tracker.models import Project, Task

from .factories import PASSWORD, make_project, make_task, make_user


class ApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = make_user("boss", manager=True)
        cls.alice = make_user("alice")
        cls.bob = make_user("bob")
        cls.project = make_project(cls.manager, [cls.alice, cls.bob])
        cls.alice_task = make_task(cls.project, cls.manager, cls.alice, "Алиса")
        cls.bob_task = make_task(cls.project, cls.manager, cls.bob, "Боб")

    def auth(self, user):
        token, _ = Token.objects.get_or_create(user=user)
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {token.key}")

    def test_anonymous_denied(self):
        resp = self.client.get(reverse("task-list"))
        self.assertEqual(resp.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_obtain_token(self):
        resp = self.client.post(reverse("api_token"), {"username": "alice", "password": PASSWORD})
        self.assertEqual(resp.status_code, 200)
        self.assertIn("token", resp.data)

    def test_list_only_own(self):
        self.auth(self.alice)
        resp = self.client.get(reverse("task-list"))
        titles = [t["title"] for t in resp.data["results"]]
        self.assertEqual(titles, ["Алиса"])

    def test_filter_by_status(self):
        self.auth(self.manager)
        resp = self.client.get(reverse("task-list"), {"status": "done"})
        self.assertEqual(resp.data["count"], 0)

    def test_idor_detail_update_delete(self):
        self.auth(self.alice)
        url = reverse("task-detail", args=[self.bob_task.pk])
        self.assertEqual(self.client.get(url).status_code, 404)
        self.assertEqual(self.client.patch(url, {"title": "x"}).status_code, 404)
        self.assertEqual(self.client.delete(url).status_code, 404)
        self.assertTrue(Task.objects.filter(pk=self.bob_task.pk).exists())

    def test_create_task_forces_author_and_assignee(self):
        self.auth(self.alice)
        resp = self.client.post(reverse("task-list"), {"project": self.project.pk, "title": "Через API"})
        self.assertEqual(resp.status_code, 201, resp.data)
        task = Task.objects.get(pk=resp.data["id"])
        self.assertEqual(task.author, self.alice)
        self.assertEqual(task.assignee, self.alice)

    def test_user_cannot_assign_other(self):
        self.auth(self.alice)
        resp = self.client.post(
            reverse("task-list"), {"project": self.project.pk, "title": "x", "assignee": self.bob.pk}
        )
        self.assertEqual(resp.status_code, 400)

    def test_assignee_can_patch_but_not_delete(self):
        self.auth(self.alice)
        url = reverse("task-detail", args=[self.alice_task.pk])
        resp = self.client.patch(url, {"status": "in_progress"})
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.delete(url).status_code, 403)

    def test_manager_assigns_and_deletes(self):
        self.auth(self.manager)
        resp = self.client.post(
            reverse("task-list"), {"project": self.project.pk, "title": "Бобу", "assignee": self.bob.pk}
        )
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(resp.data["assignee"], self.bob.pk)
        resp = self.client.delete(reverse("task-detail", args=[resp.data["id"]]))
        self.assertEqual(resp.status_code, 204)

    def test_projects_readonly_for_user(self):
        self.auth(self.alice)
        self.assertEqual(self.client.get(reverse("project-list")).status_code, 200)
        resp = self.client.post(reverse("project-list"), {"name": "мой"})
        self.assertEqual(resp.status_code, 403)

    def test_manager_creates_project(self):
        self.auth(self.manager)
        resp = self.client.post(reverse("project-list"), {"name": "API-проект", "members": [self.alice.pk]})
        self.assertEqual(resp.status_code, 201)
        self.assertEqual(Project.objects.get(name="API-проект").owner, self.manager)
