"""
Helper functions for DataTables AJAX responses
"""

from django.db.models import Q
from django.http import JsonResponse


def get_dt_params(request):
    """Extract DataTables parameters from request"""
    return {
        "draw": int(request.GET.get("draw", 1)),
        "start": int(request.GET.get("start", 0)),
        "length": min(int(request.GET.get("length", 10)), 100),
        "search": request.GET.get("search[value]", "").strip(),
    }


def apply_search(queryset, search, fields):
    """Apply search filter to queryset across multiple fields"""
    if not search:
        return queryset

    query = Q()
    for field in fields:
        query |= Q(**{f"{field}__icontains": search})
    return queryset.filter(query)


def build_dt_response(draw, total, filtered, data):
    """Build standardized DataTables JSON response"""
    return JsonResponse(
        {
            "draw": draw,
            "recordsTotal": total,
            "recordsFiltered": filtered,
            "data": data,
        }
    )
