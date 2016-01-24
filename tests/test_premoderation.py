import pytest
from django.contrib.auth import get_user_model
from django.core.urlresolvers import reverse

from pybb.models import Post, Topic

User = get_user_model()


@pytest.fixture()
def premoderation_on(settings):
    settings.PYBB_PREMODERATION = True


@pytest.mark.usefixtures('premoderation_on')
class PreModerationTestSuite(object):

    def test_premoderation(self, api_client, user, topic, admin_user):
        api_client.force_authenticate(user)
        add_post_url = reverse('pybb:post_list')
        values = {
            'topic': topic.id,
            'body': 'test premoderation'
        }
        response = api_client.post(add_post_url, values)
        assert response.status_code == 201
        post = Post.objects.get(body='test premoderation')
        assert post.on_moderation

        # Post is visible by author
        response = api_client.get(post.get_absolute_url())
        assert response.status_code == 200
        assert response.data['body'] == 'test premoderation'

        # Post is not visible by anonymous user
        api_client.force_authenticate()
        response = api_client.get(post.get_absolute_url())
        assert response.status_code == 404
        posts_url = reverse('pybb:post_list')
        response = api_client.get(posts_url, {'topic': topic.id})
        assert response.data['count'] == 0

        # But visible by superuser (with permissions)
        api_client.force_authenticate(admin_user)
        response = api_client.get(post.get_absolute_url(), follow=True)
        assert response.status_code == 200
        assert response.data['body'] == 'test premoderation'

    def test_superuser_premoderation(self, admin_user, api_client, topic):
        add_post_url = reverse('pybb:post_list')
        values = {
            'topic': topic.id,
            'body': 'test premoderation staff'
        }
        api_client.force_authenticate(admin_user)
        response = api_client.post(add_post_url, values)
        assert response.status_code == 201
        post = Post.objects.get(body='test premoderation staff')
        assert not post.on_moderation

        api_client.force_authenticate()
        response = api_client.get(post.get_absolute_url())
        assert response.data['body'] == 'test premoderation staff'

    def test_moderation(self, user, api_client, topic, admin_user):
        api_client.force_authenticate(user)
        add_post_url = reverse('pybb:post_list')
        values = {
            'topic': topic.id,
            'body': 'test premoderation'
        }
        api_client.post(add_post_url, values)
        post = Post.objects.get(topic=topic, body='test premoderation')
        assert post.on_moderation

        api_client.force_authenticate(admin_user)

        # Superuser can moderate
        moderate_url = reverse('pybb:moderate_post', kwargs={'pk': post.id})
        response = api_client.get(moderate_url)
        assert response.status_code == 405, 'Moderation requires a POST request.'

        response = api_client.post(moderate_url)
        assert response.status_code == 200
        post.refresh_from_db()
        assert not post.on_moderation

        # Now all can see this post:
        api_client.force_authenticate()
        response = api_client.get(post.get_absolute_url())
        assert response.status_code == 200
        assert response.data['body'] == 'test premoderation'

        # Other users can't moderate
        post.on_moderation = True
        post.save()
        api_client.force_authenticate(user)
        response = api_client.post(moderate_url)
        assert response.status_code == 403

    def test_topic_moderation(self, forum, user, api_client, admin_user):
        add_topic_url = reverse('pybb:topic_list')
        values = {
            'forum': forum.id,
            'body': 'new topic test',
            'name': 'new topic name',
            'poll_type': Topic.POLL_TYPE_NONE
        }
        api_client.force_authenticate(user)
        response = api_client.post(add_topic_url, values)
        assert response.status_code == 201
        assert response.data['name'] == 'new topic name'
        topic_pk = response.data['id']
        assert Topic.objects.filter(pk=topic_pk).exists()
        assert Post.objects.filter(topic__pk=topic_pk).count() == 1
        topic_url = reverse('pybb:topic', kwargs={'pk': topic_pk})
        api_client.login(username='zeus', password='zeus')  # TODO: Figure out why force_authenticate fails here
        response = api_client.get(topic_url)
        assert response.status_code == 200

        # Anon users can't view posts on moderation
        api_client.force_authenticate()
        response = api_client.get(add_topic_url, {'forum': forum.pk})  # Topic list URL is same as topic create
        assert response.status_code == 200
        assert response.data['count'] == 0

        response = api_client.get(topic_url)
        assert response.status_code == 404

        # Can view own post while it's on moderation
        api_client.login(username='zeus', password='zeus')  # TODO: Figure out why force_authenticate fails here
        response = api_client.get(add_topic_url, {'forum': forum.pk})  # Topic list URL is same as topic create
        assert response.status_code == 200
        assert response.data['count'] == 1
        serialized_topic = response.data['results'][0]
        assert serialized_topic['name'] == 'new topic name'

        response = api_client.get(topic_url)
        assert response.status_code == 200
        assert response.data['name'] == 'new topic name'

        post_pk = Post.objects.get(topic__pk=topic_pk).pk
        post_url = reverse('pybb:post', kwargs={'pk': post_pk})
        response = api_client.get(post_url)
        assert response.status_code == 200
        assert response.data['body'] == 'new topic test'

        # superusers can view posts on moderation
        api_client.force_authenticate(admin_user)
        response = api_client.get(add_topic_url, {'forum': forum.pk})  # Topic list URL is same as topic create
        assert response.status_code == 200
        assert response.data['count'] == 1
        serialized_topic = response.data['results'][0]
        assert serialized_topic['name'] == 'new topic name'

        response = api_client.get(topic_url)
        assert response.status_code == 200
        assert response.data['name'] == 'new topic name'

        response = api_client.get(post_url)
        assert response.status_code == 200
        assert response.data['body'] == 'new topic test'

        moderate_url = reverse('pybb:moderate_topic', kwargs={'pk': topic_pk})
        response = api_client.get(moderate_url)
        assert response.status_code == 405
        response = api_client.post(moderate_url)
        assert response.status_code == 200

        api_client.force_authenticate()
        response = api_client.get(add_topic_url, {'forum': forum.pk})  # Topic list URL is same as topic create
        assert response.status_code == 200
        assert response.data['count'] == 1
        serialized_topic = response.data['results'][0]
        assert serialized_topic['name'], 'new topic name'

        response = api_client.get(topic_url)
        assert response.status_code, 200
        assert response.data['name'], 'new topic name'

        response = api_client.get(post_url)
        assert response.status_code == 200
        assert response.data['body'] == 'new topic test'
