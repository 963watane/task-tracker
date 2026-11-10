from django.contrib.auth import get_user_model
from rest_framework import serializers

from ..models import Comment, Project, Task, is_manager

User = get_user_model()


class UserShortSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username"]


class ProjectSerializer(serializers.ModelSerializer):
    owner = UserShortSerializer(read_only=True)
    members = serializers.PrimaryKeyRelatedField(many=True, queryset=User.objects.all(), required=False)

    class Meta:
        model = Project
        fields = ["id", "name", "description", "owner", "members", "created_at"]


class CommentSerializer(serializers.ModelSerializer):
    author = serializers.StringRelatedField()

    class Meta:
        model = Comment
        fields = ["id", "author", "text", "created_at"]


class TaskSerializer(serializers.ModelSerializer):
    author = UserShortSerializer(read_only=True)
    status_display = serializers.CharField(source="get_status_display", read_only=True)
    comments = CommentSerializer(many=True, read_only=True)

    class Meta:
        model = Task
        fields = [
            "id",
            "project",
            "title",
            "description",
            "status",
            "status_display",
            "priority",
            "author",
            "assignee",
            "due_date",
            "created_at",
            "updated_at",
            "comments",
        ]
        read_only_fields = ["created_at", "updated_at"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            # в выпадающем списке Browsable API только свои проекты
            self.fields["project"].queryset = Project.objects.visible_for(request.user)

    def validate(self, attrs):
        user = self.context["request"].user
        project = attrs.get("project") or getattr(self.instance, "project", None)
        assignee = attrs.get("assignee", getattr(self.instance, "assignee", None))
        if not is_manager(user):
            if assignee and assignee != user:
                raise serializers.ValidationError({"assignee": "Можно назначать задачи только на себя."})
        if project and assignee and not project.has_member(assignee):
            raise serializers.ValidationError({"assignee": "Исполнитель не состоит в этом проекте."})
        return attrs
