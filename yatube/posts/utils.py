from django.core.paginator import Paginator

LIMIT = 10


def get_pagin(queryset, request):
    paginator = Paginator(queryset, LIMIT)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    return {'page_obj': page_obj}
