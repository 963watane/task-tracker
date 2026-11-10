from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

from tracker.models import Project, Task

User = get_user_model()
PASSWORD = "Test-pass-123"


def make_user(username, manager=False):
    user = User.objects.create_user(username=username, password=PASSWORD, email=f"{username}@test.local")
    if manager:
        user.groups.add(Group.objects.get(name="Менеджер"))
    return user


def make_project(owner, members=(), name="Проект"):
    project = Project.objects.create(name=name, owner=owner)
    project.members.set(members)
    return project


def make_task(project, author, assignee=None, title="Задача", **kwargs):
    return Task.objects.create(project=project, author=author, assignee=assignee, title=title, **kwargs)
