from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .admin_views import (
    AdminArticleCreateView,
    AdminArticleDetailView,
    AdminArticleListView,
    AdminCategoryDetailView,
    AdminCategoryListCreateView,
    AdminCommentApproveView,
    AdminCommentDeleteView,
    AdminCommentListView,
    AdminPaymentListView,
    AdminSiteSettingsView,
    AdminSubscriptionListView,
    AdminSummaryView,
    AdminTagDetailView,
    AdminTagListCreateView,
    AdminUserListView,
)
from .views import ChangePasswordView, LoginView, LogoutView, MeView, RegisterView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("token/refresh/", TokenRefreshView.as_view(), name="token-refresh"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("password/change/", ChangePasswordView.as_view(), name="auth-password-change"),
    # Admin endpoints
    path("admin/summary/", AdminSummaryView.as_view(), name="admin-summary"),
    path("admin/users/", AdminUserListView.as_view(), name="admin-users"),
    # Admin article CRUD
    path("admin/articles/", AdminArticleListView.as_view(), name="admin-articles"),
    path("admin/articles/create/", AdminArticleCreateView.as_view(), name="admin-article-create"),
    path("admin/articles/<uuid:pk>/", AdminArticleDetailView.as_view(), name="admin-article-detail"),
    # Admin category CRUD
    path("admin/categories/", AdminCategoryListCreateView.as_view(), name="admin-categories"),
    path("admin/categories/<int:pk>/", AdminCategoryDetailView.as_view(), name="admin-category-detail"),
    # Admin tag CRUD
    path("admin/tags/", AdminTagListCreateView.as_view(), name="admin-tags"),
    path("admin/tags/<int:pk>/", AdminTagDetailView.as_view(), name="admin-tag-detail"),
    # Admin comment moderation
    path("admin/comments/", AdminCommentListView.as_view(), name="admin-comments"),
    path("admin/comments/<uuid:pk>/approve/", AdminCommentApproveView.as_view(), name="admin-comment-approve"),
    path("admin/comments/<uuid:pk>/", AdminCommentDeleteView.as_view(), name="admin-comment-delete"),
    # Admin subscriptions / payments (read-only)
    path("admin/subscriptions/", AdminSubscriptionListView.as_view(), name="admin-subscriptions"),
    path("admin/payments/", AdminPaymentListView.as_view(), name="admin-payments"),
    # Site settings
    path("admin/settings/", AdminSiteSettingsView.as_view(), name="admin-site-settings"),
]
