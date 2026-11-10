from django.test import TestCase

from tracker.models import Project, Task, is_manager

from .factories import make_project, make_task, make_user


class ModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = make_user("boss", manager=True)
        cls.alice = make_user("alice")
        cls.bob = make_user("bob")
        cls.outsider = make_user("eve")
        cls.project = make_project(cls.manager, [cls.alice, cls.bob])
        cls.t_alice = make_task(cls.project, cls.manager, cls.alice, "для Алисы")
        cls.t_bob = make_task(cls.project, cls.manager, cls.bob, "для Боба")
        cls.t_by_alice = make_task(cls.project, cls.alice, None, "Алиса создала")

    def test_str_and_url(self):
        self.assertEqual(str(self.t_alice), "для Алисы")
        self.assertEqual(self.t_alice.get_absolute_url(), f"/tasks/{self.t_alice.pk}/")
        self.assertEqual(str(self.project), "Проект")

    def test_default_status(self):
        self.assertEqual(self.t_alice.status, Task.Status.TODO)

    def test_manager_permission_from_group(self):
        self.assertTrue(is_manager(self.manager))
        self.assertFalse(is_manager(self.alice))

    def test_user_sees_only_own_tasks(self):
        visible = set(Task.objects.visible_for(self.alice))
        self.assertEqual(visible, {self.t_alice, self.t_by_alice})

    def test_manager_sees_all_tasks(self):
        self.assertEqual(Task.objects.visible_for(self.manager).count(), 3)

    def test_projects_visible_for_members_only(self):
        self.assertIn(self.project, Project.objects.visible_for(self.alice))
        self.assertNotIn(self.project, Project.objects.visible_for(self.outsider))

    def test_has_member(self):
        self.assertTrue(self.project.has_member(self.manager))  # владелец
        self.assertTrue(self.project.has_member(self.bob))
        self.assertFalse(self.project.has_member(self.outsider))

    def test_can_edit_and_delete(self):
        self.assertTrue(self.t_alice.can_edit(self.alice))  # исполнитель
        self.assertFalse(self.t_alice.can_delete(self.alice))  # но не автор
        self.assertTrue(self.t_by_alice.can_delete(self.alice))
        self.assertFalse(self.t_bob.can_edit(self.alice))
        self.assertTrue(self.t_bob.can_delete(self.manager))
