from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import (
    ArticleDetailView,
    ArticleListCreateView,
    CategoryViewSet,
    ImageUploadView,
    IncrementArticleView,
    MyArticlesView,
    PublishArticleView,
    TagViewSet,
    MyArticleStatsView,
)

router = DefaultRouter()
router.register("categories", CategoryViewSet, basename="category")
router.register("tags", TagViewSet, basename="tag")

urlpatterns = [
    path("articles/", ArticleListCreateView.as_view(), name="article-list-create"),
    path("articles/upload-image/", ImageUploadView.as_view(), name="article-upload-image"),
    path("articles/my/", MyArticlesView.as_view(), name="article-my-list"),
    path("articles/my/stats/", MyArticleStatsView.as_view(), name="article-my-stats"),
    path("articles/<str:identifier>/", ArticleDetailView.as_view(), name="article-detail"),
    path("articles/<uuid:pk>/publish/", PublishArticleView.as_view(), name="article-publish"),
    path("articles/<uuid:pk>/increment_view/", IncrementArticleView.as_view(), name="article-increment-view"),
    path("", include(router.urls)),
]
