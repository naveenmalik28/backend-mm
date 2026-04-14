from django.urls import path

from .views import ArticleCommentListCreateView, CommentDeleteView

urlpatterns = [
    path("articles/<uuid:article_id>/comments/", ArticleCommentListCreateView.as_view(), name="article-comments"),
    path("comments/<uuid:pk>/", CommentDeleteView.as_view(), name="comment-delete"),
]
