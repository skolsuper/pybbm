from rest_framework.pagination import PageNumberPagination

from pybb.settings import settings


class PybbTopicPagination(PageNumberPagination):
    page_size = settings.PYBB_DEFAULT_TOPICS_PER_PAGE
    max_page_size = settings.PYBB_MAX_TOPICS_PER_PAGE
    page_size_query_param = 'page_size'


class PybbPostPagination(PageNumberPagination):
    page_size = settings.PYBB_DEFAULT_POSTS_PER_PAGE
    max_page_size = settings.PYBB_MAX_POSTS_PER_PAGE
    page_size_query_param = 'page_size'
