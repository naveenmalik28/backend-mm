from django.db.models import Count, F, Q
from django.shortcuts import get_object_or_404
from rest_framework.exceptions import PermissionDenied
from rest_framework import generics, permissions, status, viewsets
from rest_framework.response import Response
from rest_framework.views import APIView

from ..users.permissions import IsSubscriber

from .filters import filter_article_queryset
from .models import Article, Category, Tag
from .pagination import ArticlePagination
from .serializers import ArticleSerializer, ArticleDetailSerializer, CategorySerializer, TagSerializer
from django.core.files.storage import default_storage
from rest_framework.parsers import MultiPartParser, FormParser

class ImageUploadView(APIView):
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        if 'image' not in request.FILES:
            return Response({"error": "No image provided"}, status=status.HTTP_400_BAD_REQUEST)
        
        image_file = request.FILES['image']
        file_name = default_storage.save(f"articles/covers/{image_file.name}", image_file)
        file_url = request.build_absolute_uri(default_storage.url(file_name))
        
        return Response({"url": file_url})


class ArticleListCreateView(generics.ListCreateAPIView):
    serializer_class = ArticleSerializer
    pagination_class = ArticlePagination

    def get_permissions(self):
        if self.request.method == "POST":
            if self.request.user and self.request.user.is_authenticated and self.request.user.is_staff:
                return [permissions.IsAuthenticated()]
            return [permissions.IsAuthenticated(), IsSubscriber()]
        return [permissions.AllowAny()]

    def get_queryset(self):
        queryset = Article.objects.select_related("author", "category").prefetch_related("tags")
        if self.request.user.is_authenticated:
            queryset = queryset.filter(Q(status=Article.STATUS_PUBLISHED) | Q(author=self.request.user))
        else:
            queryset = queryset.filter(status=Article.STATUS_PUBLISHED)
        return filter_article_queryset(queryset, self.request.query_params)

    def perform_create(self, serializer):
        serializer.save(author=self.request.user)


class ArticleDetailView(APIView):
    def get_permissions(self):
        if self.request.method == "GET":
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get_object(self, identifier, request):
        queryset = Article.objects.select_related("author", "category").prefetch_related("tags")
        if request.method == "GET":
            article = get_object_or_404(queryset, slug=identifier)
            if article.status != Article.STATUS_PUBLISHED:
                if not request.user.is_authenticated or (article.author != request.user and not request.user.is_staff):
                    raise PermissionDenied("You do not have access to this article.")
            return article
        article = get_object_or_404(queryset, pk=identifier)
        if article.author != request.user and not request.user.is_staff:
            raise PermissionDenied("You do not own this article.")
        return article

    def get(self, request, identifier):
        return Response(ArticleDetailSerializer(self.get_object(identifier, request)).data)

    def patch(self, request, identifier):
        article = self.get_object(identifier, request)
        serializer = ArticleSerializer(article, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, identifier):
        article = self.get_object(identifier, request)
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class PublishArticleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        if article.author != request.user and not request.user.is_staff:
            raise PermissionDenied("You do not own this article.")
        article.status = Article.STATUS_PUBLISHED
        article.save()
        return Response({"status": "published"})


class IncrementArticleView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, pk):
        get_object_or_404(Article, pk=pk)
        Article.objects.filter(pk=pk).update(view_count=F("view_count") + 1)
        return Response({"status": "ok"})


class MyArticlesView(generics.ListAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = ArticleSerializer
    pagination_class = ArticlePagination

    def get_queryset(self):
        queryset = Article.objects.filter(author=self.request.user).select_related("author", "category").prefetch_related("tags")
        return filter_article_queryset(queryset, self.request.query_params)


class CategoryAccessPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class TagAccessPermission(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in permissions.SAFE_METHODS:
            return True
        if request.method == "POST":
            return bool(request.user and request.user.is_authenticated)
        return bool(request.user and request.user.is_authenticated and request.user.is_staff)


class CategoryViewSet(viewsets.ModelViewSet):
    serializer_class = CategorySerializer
    permission_classes = [CategoryAccessPermission]
    pagination_class = None

    def get_queryset(self):
        return Category.objects.annotate(article_count=Count("articles")).order_by("name")


class TagViewSet(viewsets.ModelViewSet):
    serializer_class = TagSerializer
    permission_classes = [TagAccessPermission]
    pagination_class = None

    def get_queryset(self):
        return Tag.objects.annotate(article_count=Count("articles")).order_by("name")


# Create your views here.
