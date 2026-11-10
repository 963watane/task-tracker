import datetime

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.management.base import BaseCommand
from django.utils import timezone

from tracker.models import Comment, Project, Task

DEMO_PASSWORD = "Demo-pass-2026"


class Command(BaseCommand):
    help = "Создаёт демо-пользователей, проекты и задачи (можно запускать повторно)"

    def handle(self, *args, **options):
        User = get_user_model()
        users = {}
        for name in ["manager", "alice", "bob"]:
            user, created = User.objects.get_or_create(username=name, defaults={"email": f"{name}@example.com"})
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            users[name] = user
        users["manager"].groups.add(Group.objects.get(name="Менеджер"))

        if Project.objects.exists():
            self.stdout.write("Данные уже есть, пропускаю.")
            return

        today = timezone.localdate()
        backend = Project.objects.create(
            name="Backend API", description="REST API для мобильного приложения", owner=users["manager"]
        )
        backend.members.set([users["alice"], users["bob"]])
        site = Project.objects.create(
            name="Сайт компании", description="Редизайн и перенос на Django", owner=users["manager"]
        )
        site.members.set([users["alice"]])

        S = Task.Status
        data = [
            (backend, "Модели и миграции", S.DONE, 3, "alice", -5),
            (backend, "Эндпоинт /api/tasks/", S.IN_PROGRESS, 3, "alice", 2),
            (backend, "Токен-аутентификация", S.TODO, 2, "bob", 5),
            (backend, "Тесты на права доступа", S.TODO, 3, "bob", 7),
            (site, "Вёрстка главной", S.IN_PROGRESS, 2, "alice", 3),
            (site, "Форма обратной связи", S.TODO, 1, "alice", 10),
        ]
        for project, title, status, prio, who, days in data:
            Task.objects.create(
                project=project,
                title=title,
                status=status,
                priority=prio,
                author=users["manager"],
                assignee=users[who],
                due_date=today + datetime.timedelta(days=days),
            )
        t = Task.objects.get(title="Эндпоинт /api/tasks/")
        Comment.objects.create(task=t, author=users["manager"], text="Не забудь про пагинацию")
        self.stdout.write(self.style.SUCCESS(f"Готово. Логины: manager, alice, bob / пароль {DEMO_PASSWORD}"))
