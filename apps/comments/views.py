from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.articles.models import Article

from .models import Comment
from .serializers import CommentSerializer


class ArticleCommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer

    def get_permissions(self):
        if self.request.method == "POST":
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        article = get_object_or_404(Article, pk=self.kwargs["article_id"])
        return Comment.objects.filter(article=article, is_approved=True).select_related("author", "parent")

    def perform_create(self, serializer):
        article = get_object_or_404(Article, pk=self.kwargs["article_id"])
        serializer.save(article=article, author=self.request.user)


class CommentDeleteView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        if comment.author != request.user and not request.user.is_staff:
            raise PermissionDenied("You do not own this comment.")
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# Create your views here.
