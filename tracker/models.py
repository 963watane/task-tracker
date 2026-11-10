from django.conf import settings
from django.db import models
from django.db.models import Q
from django.urls import reverse

MANAGER_PERM = "tracker.view_all_tasks"


def is_manager(user):
    return user.is_authenticated and user.has_perm(MANAGER_PERM)


class ProjectQuerySet(models.QuerySet):
    def visible_for(self, user):
        if is_manager(user):
            return self.all()
        return self.filter(Q(owner=user) | Q(members=user)).distinct()


class Project(models.Model):
    name = models.CharField("название", max_length=120)
    description = models.TextField("описание", blank=True)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="owned_projects",
        verbose_name="владелец",
    )
    members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="projects",
        blank=True,
        verbose_name="участники",
    )
    created_at = models.DateTimeField("создан", auto_now_add=True)

    objects = ProjectQuerySet.as_manager()

    class Meta:
        verbose_name = "проект"
        verbose_name_plural = "проекты"
        ordering = ["name"]

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("tracker:project_detail", args=[self.pk])

    def has_member(self, user):
        return self.owner_id == user.id or self.members.filter(pk=user.pk).exists()


class TaskQuerySet(models.QuerySet):
    def visible_for(self, user):
        """Обычный пользователь видит только свои задачи (автор или исполнитель)."""
        if is_manager(user):
            return self.all()
        return self.filter(Q(author=user) | Q(assignee=user))


class Task(models.Model):
    class Status(models.TextChoices):
        TODO = "todo", "To Do"
        IN_PROGRESS = "in_progress", "In Progress"
        DONE = "done", "Done"

    class Priority(models.IntegerChoices):
        LOW = 1, "низкий"
        NORMAL = 2, "обычный"
        HIGH = 3, "высокий"

    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name="tasks", verbose_name="проект")
    title = models.CharField("заголовок", max_length=200)
    description = models.TextField("описание", blank=True)
    status = models.CharField("статус", max_length=20, choices=Status.choices, default=Status.TODO)
    priority = models.PositiveSmallIntegerField("приоритет", choices=Priority.choices, default=Priority.NORMAL)
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="created_tasks",
        verbose_name="автор",
    )
    assignee = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks",
        verbose_name="исполнитель",
    )
    due_date = models.DateField("срок", null=True, blank=True)
    created_at = models.DateTimeField("создана", auto_now_add=True)
    updated_at = models.DateTimeField("изменена", auto_now=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        verbose_name = "задача"
        verbose_name_plural = "задачи"
        ordering = ["status", "-priority", "due_date"]
        permissions = [("view_all_tasks", "Может видеть все задачи (менеджер)")]
        indexes = [models.Index(fields=["status"]), models.Index(fields=["assignee", "status"])]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("tracker:task_detail", args=[self.pk])

    def can_edit(self, user):
        return is_manager(user) or user.id in (self.author_id, self.assignee_id)

    def can_delete(self, user):
        return is_manager(user) or user.id == self.author_id


class Comment(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="comments", verbose_name="задача")
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, verbose_name="автор")
    text = models.TextField("текст", max_length=2000)
    created_at = models.DateTimeField("создан", auto_now_add=True)

    class Meta:
        verbose_name = "комментарий"
        verbose_name_plural = "комментарии"
        ordering = ["created_at"]

    def __str__(self):
        return f"{self.author}: {self.text[:30]}"
