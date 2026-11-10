from django.db import migrations

MANAGER_GROUP = "Менеджер"
PERMS = [
    "view_all_tasks",
    "add_project", "change_project", "delete_project", "view_project",
    "add_task", "change_task", "delete_task", "view_task",
]


def create_group(apps, schema_editor):
    from django.contrib.auth.management import create_permissions

    # права создаются после миграций, поэтому создаём их явно
    for app_config in apps.get_app_configs():
        app_config.models_module = True
        create_permissions(app_config, verbosity=0)
        app_config.models_module = None

    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    group, _ = Group.objects.get_or_create(name=MANAGER_GROUP)
    group.permissions.set(Permission.objects.filter(content_type__app_label="tracker", codename__in=PERMS))


def remove_group(apps, schema_editor):
    apps.get_model("auth", "Group").objects.filter(name=MANAGER_GROUP).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("tracker", "0001_initial"),
        ("auth", "0012_alter_user_first_name_max_length"),
        ("contenttypes", "0002_remove_content_type_name"),
    ]

    operations = [migrations.RunPython(create_group, remove_group)]
