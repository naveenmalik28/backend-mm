from rest_framework import serializers

from apps.users.serializers import UserSerializer

from .models import Comment


class CommentSerializer(serializers.ModelSerializer):
    author = UserSerializer(read_only=True)

    class Meta:
        model = Comment
        fields = ("id", "article", "author", "parent", "body", "is_approved", "created_at", "updated_at")
        read_only_fields = ("id", "article", "author", "is_approved", "created_at", "updated_at")

