from django.contrib.auth import get_user_model
from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.articles.models import Article, Category, Tag, SiteSettings
from apps.articles.serializers import (
    ArticleSerializer,
    CategorySerializer,
    TagSerializer,
    SiteSettingsSerializer,
    AdminCommentSerializer,
)
from apps.comments.models import Comment
from apps.subscriptions.models import Payment, Plan, Subscription
from apps.subscriptions.serializers import AdminPlanSerializer, PaymentSerializer, SubscriptionSerializer

from .serializers import UserSerializer

User = get_user_model()


class AdminSummaryView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        return Response({
            "users": User.objects.count(),
            "articles": Article.objects.count(),
            "published_articles": Article.objects.filter(status=Article.STATUS_PUBLISHED).count(),
            "draft_articles": Article.objects.filter(status=Article.STATUS_DRAFT).count(),
            "categories": Category.objects.count(),
            "tags": Tag.objects.count(),
            "comments": Comment.objects.count(),
            "pending_comments": Comment.objects.filter(is_approved=False).count(),
            "subscriptions": Subscription.objects.count(),
            "active_subscriptions": Subscription.objects.filter(status=Subscription.STATUS_ACTIVE).count(),
            "payments": Payment.objects.count(),
            "recent_articles": ArticleSerializer(
                Article.objects.select_related("author", "category").prefetch_related("tags").order_by("-created_at")[:5],
                many=True,
            ).data,
        })


class AdminUserListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = UserSerializer
    pagination_class = None
    queryset = User.objects.all().order_by("-date_joined")


# ---------------------------------------------------------------------------
# Article admin CRUD
# ---------------------------------------------------------------------------

class AdminArticleListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = ArticleSerializer
    pagination_class = None
    queryset = Article.objects.select_related("author", "category").prefetch_related("tags").all()


class AdminArticleCreateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = ArticleSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(author=request.user)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminArticleDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        article = get_object_or_404(
            Article.objects.select_related("author", "category").prefetch_related("tags"),
            pk=pk,
        )
        return Response(ArticleSerializer(article).data)

    def patch(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        serializer = ArticleSerializer(article, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        article = get_object_or_404(Article, pk=pk)
        article.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Category admin CRUD (with update)
# ---------------------------------------------------------------------------

class AdminCategoryListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = CategorySerializer
    pagination_class = None

    def get_queryset(self):
        return Category.objects.annotate(article_count=Count("articles"))


class AdminCategoryDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        serializer = CategorySerializer(category, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        category = get_object_or_404(Category, pk=pk)
        category.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Tag admin CRUD (with update)
# ---------------------------------------------------------------------------

class AdminTagListCreateView(generics.ListCreateAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = TagSerializer
    pagination_class = None

    def get_queryset(self):
        return Tag.objects.annotate(article_count=Count("articles"))


class AdminTagDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def patch(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        serializer = TagSerializer(tag, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        tag = get_object_or_404(Tag, pk=pk)
        tag.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Comment admin (list, approve, delete)
# ---------------------------------------------------------------------------

class AdminCommentListView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        comments = Comment.objects.select_related("author", "article").order_by("-created_at")
        return Response(AdminCommentSerializer(comments, many=True).data)


class AdminCommentApproveView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        comment.is_approved = not comment.is_approved
        comment.save()
        return Response({"is_approved": comment.is_approved})


class AdminCommentDeleteView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def delete(self, request, pk):
        comment = get_object_or_404(Comment, pk=pk)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Subscription / Payment (read-only)
# ---------------------------------------------------------------------------

class AdminSubscriptionListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = SubscriptionSerializer
    pagination_class = None
    queryset = Subscription.objects.select_related("plan", "user").prefetch_related("payments").all()


class AdminPaymentListView(generics.ListAPIView):
    permission_classes = [permissions.IsAdminUser]
    serializer_class = PaymentSerializer
    pagination_class = None
    queryset = Payment.objects.select_related("user", "subscription").all()


# ---------------------------------------------------------------------------
# Plan admin CRUD
# ---------------------------------------------------------------------------

class AdminPlanListCreateView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        plans = Plan.objects.annotate(subscription_count=Count("subscriptions")).order_by("sort_order", "price", "id")
        return Response(AdminPlanSerializer(plans, many=True).data)

    def post(self, request):
        serializer = AdminPlanSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class AdminPlanDetailView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request, pk):
        plan = get_object_or_404(
            Plan.objects.annotate(subscription_count=Count("subscriptions")),
            pk=pk,
        )
        return Response(AdminPlanSerializer(plan).data)

    def patch(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        serializer = AdminPlanSerializer(plan, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def delete(self, request, pk):
        plan = get_object_or_404(Plan, pk=pk)
        if plan.subscriptions.exists():
            return Response(
                {"error": "Cannot delete plan with existing subscriptions."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        plan.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


# ---------------------------------------------------------------------------
# Site Settings (singleton GET/PUT)
# ---------------------------------------------------------------------------

class AdminSiteSettingsView(APIView):
    permission_classes = [permissions.IsAdminUser]

    def get(self, request):
        settings = SiteSettings.load()
        return Response(SiteSettingsSerializer(settings).data)

    def put(self, request):
        settings = SiteSettings.load()
        serializer = SiteSettingsSerializer(settings, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)
