from django.contrib import admin

from .models import Comment, Project, Task


class TaskInline(admin.TabularInline):
    model = Task
    extra = 0
    fields = ["title", "status", "priority", "assignee", "due_date"]
    autocomplete_fields = ["assignee"]


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ["name", "owner", "created_at"]
    search_fields = ["name"]
    list_filter = ["created_at"]
    filter_horizontal = ["members"]
    inlines = [TaskInline]


class CommentInline(admin.TabularInline):
    model = Comment
    extra = 0


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ["title", "project", "status", "priority", "assignee", "due_date"]
    list_filter = ["status", "priority", "project", "assignee"]
    list_editable = ["status"]
    search_fields = ["title", "description"]
    list_select_related = ["project", "assignee"]
    autocomplete_fields = ["assignee", "author"]
    date_hierarchy = "created_at"
    inlines = [CommentInline]


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ["task", "author", "created_at"]
    list_select_related = ["task", "author"]
