from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse_lazy
from django.views import View
from django.views.generic import CreateView, DeleteView, DetailView, ListView, UpdateView

from .forms import CommentForm, ProjectForm, StatusForm, TaskForm
from .models import Project, Task, is_manager


class VisibleTasksMixin(LoginRequiredMixin):
    """Все представления задач берут queryset только из задач, доступных пользователю.
    Чужая задача по прямому id -> 404 (а не 403, чтобы не выдавать что она существует)."""

    def get_queryset(self):
        return Task.objects.visible_for(self.request.user).select_related("project", "assignee", "author")


# ---------- задачи ----------


class TaskListView(VisibleTasksMixin, ListView):
    template_name = "tracker/task_list.html"
    context_object_name = "tasks"
    paginate_by = 20

    def get_queryset(self):
        qs = super().get_queryset()
        status = self.request.GET.get("status")
        if status in Task.Status.values:
            qs = qs.filter(status=status)
        project = self.request.GET.get("project")
        if project and project.isdigit():
            qs = qs.filter(project_id=project)
        if self.request.GET.get("mine"):
            qs = qs.filter(assignee=self.request.user)
        return qs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["statuses"] = Task.Status.choices
        ctx["projects"] = Project.objects.visible_for(self.request.user)
        ctx["current_status"] = self.request.GET.get("status", "")
        ctx["current_project"] = self.request.GET.get("project", "")
        return ctx


class TaskDetailView(VisibleTasksMixin, DetailView):
    template_name = "tracker/task_detail.html"
    context_object_name = "task"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["comments"] = self.object.comments.select_related("author")
        ctx["comment_form"] = CommentForm()
        ctx["status_form"] = StatusForm(instance=self.object)
        ctx["can_edit"] = self.object.can_edit(self.request.user)
        ctx["can_delete"] = self.object.can_delete(self.request.user)
        return ctx


class TaskCreateView(LoginRequiredMixin, CreateView):
    model = Task
    form_class = TaskForm
    template_name = "tracker/task_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def get_initial(self):
        initial = super().get_initial()
        if self.request.GET.get("project"):
            initial["project"] = self.request.GET["project"]
        return initial

    def form_valid(self, form):
        form.instance.author = self.request.user
        if not is_manager(self.request.user):
            form.instance.assignee = self.request.user
        messages.success(self.request, "Задача создана.")
        return super().form_valid(form)


class TaskUpdateView(VisibleTasksMixin, UpdateView):
    form_class = TaskForm
    template_name = "tracker/task_form.html"

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs["user"] = self.request.user
        return kwargs

    def form_valid(self, form):
        messages.success(self.request, "Задача сохранена.")
        return super().form_valid(form)


class TaskDeleteView(VisibleTasksMixin, DeleteView):
    template_name = "tracker/task_confirm_delete.html"
    success_url = reverse_lazy("tracker:task_list")

    def get_queryset(self):
        qs = super().get_queryset()
        if is_manager(self.request.user):
            return qs
        return qs.filter(author=self.request.user)

    def form_valid(self, form):
        messages.success(self.request, "Задача удалена.")
        return super().form_valid(form)


class TaskStatusView(LoginRequiredMixin, View):
    """Быстрая смена статуса с карточки задачи (только POST)."""

    http_method_names = ["post"]

    def post(self, request, pk):
        task = get_object_or_404(Task.objects.visible_for(request.user), pk=pk)
        form = StatusForm(request.POST, instance=task)
        if form.is_valid():
            form.save()
            messages.success(request, f"Статус: {task.get_status_display()}")
        return redirect(task)


class CommentCreateView(LoginRequiredMixin, View):
    http_method_names = ["post"]

    def post(self, request, pk):
        task = get_object_or_404(Task.objects.visible_for(request.user), pk=pk)
        form = CommentForm(request.POST)
        if form.is_valid():
            comment = form.save(commit=False)
            comment.task = task
            comment.author = request.user
            comment.save()
        return redirect(task)


# ---------- проекты ----------


class ProjectListView(LoginRequiredMixin, ListView):
    template_name = "tracker/project_list.html"
    context_object_name = "projects"

    def get_queryset(self):
        return (
            Project.objects.visible_for(self.request.user)
            .select_related("owner")
            .annotate(
                total=Count("tasks", distinct=True),
                done=Count("tasks", filter=Q(tasks__status=Task.Status.DONE), distinct=True),
            )
        )


class ProjectDetailView(LoginRequiredMixin, DetailView):
    template_name = "tracker/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        return Project.objects.visible_for(self.request.user).prefetch_related("members")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["tasks"] = (
            Task.objects.visible_for(self.request.user).filter(project=self.object).select_related("assignee")
        )
        return ctx


class ManagerOnlyMixin(LoginRequiredMixin, PermissionRequiredMixin):
    raise_exception = True  # залогиненный без прав получает 403, а не редирект на логин


class ProjectCreateView(ManagerOnlyMixin, CreateView):
    permission_required = "tracker.add_project"
    model = Project
    form_class = ProjectForm
    template_name = "tracker/project_form.html"

    def form_valid(self, form):
        form.instance.owner = self.request.user
        messages.success(self.request, "Проект создан.")
        return super().form_valid(form)


class ProjectUpdateView(ManagerOnlyMixin, UpdateView):
    permission_required = "tracker.change_project"
    model = Project
    form_class = ProjectForm
    template_name = "tracker/project_form.html"


class ProjectDeleteView(ManagerOnlyMixin, DeleteView):
    permission_required = "tracker.delete_project"
    model = Project
    template_name = "tracker/project_confirm_delete.html"
    success_url = reverse_lazy("tracker:project_list")
