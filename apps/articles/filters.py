from django.db.models import Q


def filter_article_queryset(queryset, params):
    search = params.get("search")
    status = params.get("status")
    category_slug = params.get("category__slug") or params.get("category")
    tag_slug = params.get("tags__slug") or params.get("tag")
    ordering = params.get("ordering")

    if search:
        queryset = queryset.filter(
            Q(title__icontains=search)
            | Q(excerpt__icontains=search)
            | Q(content__icontains=search)
        )
    if status:
        queryset = queryset.filter(status=status)
    if category_slug:
        queryset = queryset.filter(category__slug=category_slug)
    if tag_slug:
        queryset = queryset.filter(tags__slug=tag_slug)
    if ordering in {"published_at", "-published_at", "view_count", "-view_count", "created_at", "-created_at"}:
        queryset = queryset.order_by(ordering)

    return queryset.distinct()

