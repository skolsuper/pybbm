from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.http import Http404
from rest_framework.exceptions import NotFound

from pybb.models import Post
from pybb.util import get_pybb_profile_model
from pybb.views import CategoryView, ForumView, TopicView, PostView

User = get_user_model()
Profile = get_pybb_profile_model()
Exc404 = (Http404, NotFound)


def test_hidden_category(rf, category, user, admin_user):
    category.hidden = True
    category.save()
    # access without user should get 404
    category_view_func = CategoryView.as_view()
    request = rf.get(category.get_absolute_url())
    request.user = AnonymousUser()
    response = category_view_func(request, pk=category.pk)
    assert response.status_code == 404
    # access with (unauthorized) user should get 404
    request.user = user
    response = category_view_func(request, pk=category.pk)
    assert response.status_code == 404
    # allowed user is allowed
    request.user = admin_user
    response = category_view_func(request, pk=category.pk)
    assert response.status_code == 200


def test_hidden_forum(rf, forum, user, admin_user):
    forum.hidden = True
    forum.save()
    # access without user should get 404
    forum_view_func = ForumView.as_view()
    request = rf.get(forum.get_absolute_url())
    request.user = AnonymousUser()
    response = forum_view_func(request, pk=forum.pk)
    assert response.status_code == 404
    # access with (unauthorized) user should get 404
    request.user = user
    response = forum_view_func(request, pk=forum.pk)
    assert response.status_code == 404
    # allowed user is allowed
    request.user = admin_user
    response = forum_view_func(request, pk=forum.pk)
    assert response.status_code == 200


def test_hidden_topic(rf, user, admin_user, topic):
    topic.forum.hidden = True
    topic.forum.save()

    topic_view_func = TopicView.as_view()
    request = rf.get(topic.get_absolute_url())
    # access without user should be redirected
    request.user = AnonymousUser()
    response = topic_view_func(request, pk=topic.pk)
    assert response.status_code == 404
    # access with (unauthorized) user should get 403 (forbidden)
    request.user = user
    response = topic_view_func(request, pk=topic.pk)
    assert response.status_code == 404
    # allowed user is allowed
    request.user = admin_user
    response = topic_view_func(request, pk=topic.pk)
    assert response.status_code == 200


def test_hidden_post(rf, topic, user, admin_user):
    topic.forum.hidden = True
    topic.forum.save()
    post = Post.objects.create(topic=topic, user=admin_user, user_ip='0.0.0.0', body='test hidden post')
    post_view_func = PostView.as_view()

    # access without user should be redirected
    request = rf.get(post.get_absolute_url())
    request.user = AnonymousUser()
    response = post_view_func(request, pk=post.pk)
    assert response.status_code == 404

    # access with (unauthorized) user should get 403 (forbidden)
    request.user = user
    response = post_view_func(request, pk=post.pk)
    assert response.status_code == 404

    # allowed user is allowed
    request.user = admin_user
    response = post_view_func(request, pk=post.pk)
    assert response.status_code == 200
