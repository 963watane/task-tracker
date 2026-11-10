from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated

from ..models import Project, Task, is_manager
from .permissions import CanEditTask, IsManagerOrReadOnly
from .serializers import ProjectSerializer, TaskSerializer


class ProjectViewSet(viewsets.ModelViewSet):
    serializer_class = ProjectSerializer
    permission_classes = [IsAuthenticated, IsManagerOrReadOnly]

    def get_queryset(self):
        return Project.objects.visible_for(self.request.user).select_related("owner").prefetch_related("members")

    def perform_create(self, serializer):
        serializer.save(owner=self.request.user)


class TaskViewSet(viewsets.ModelViewSet):
    serializer_class = TaskSerializer
    permission_classes = [IsAuthenticated, CanEditTask]

    def get_queryset(self):
        qs = (
            Task.objects.visible_for(self.request.user)
            .select_related("author", "assignee", "project")
            .prefetch_related("comments__author")
        )
        status = self.request.query_params.get("status")
        if status:
            qs = qs.filter(status=status)
        return qs

    def perform_create(self, serializer):
        extra = {"author": self.request.user}
        if not is_manager(self.request.user):
            extra["assignee"] = self.request.user
        serializer.save(**extra)
