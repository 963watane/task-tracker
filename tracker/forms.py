from django import forms
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import Comment, Project, Task, is_manager

User = get_user_model()


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = ["name", "description", "members"]
        widgets = {"members": forms.CheckboxSelectMultiple}


class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["project", "title", "description", "status", "priority", "assignee", "due_date"]
        widgets = {"due_date": forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d")}

    def __init__(self, *args, user, **kwargs):
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["project"].queryset = Project.objects.visible_for(user)
        if is_manager(user):
            self.fields["assignee"].queryset = User.objects.filter(is_active=True).order_by("username")
        else:
            # обычный пользователь назначает задачу только на себя
            self.fields["assignee"].queryset = User.objects.filter(pk=user.pk)
            self.fields["assignee"].initial = user.pk

    def clean_due_date(self):
        due = self.cleaned_data.get("due_date")
        if due and due < timezone.localdate() and not self.instance.pk:
            raise forms.ValidationError("Срок не может быть в прошлом.")
        return due

    def clean(self):
        cleaned = super().clean()
        project = cleaned.get("project")
        assignee = cleaned.get("assignee")
        if project and assignee and not project.has_member(assignee):
            self.add_error("assignee", "Исполнитель не состоит в этом проекте.")
        return cleaned


class StatusForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ["status"]


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ["text"]
        widgets = {"text": forms.Textarea(attrs={"rows": 2, "placeholder": "Комментарий..."})}
        labels = {"text": ""}
