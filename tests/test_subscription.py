# coding=utf-8
from __future__ import unicode_literals

from django.core import mail
from django.core.urlresolvers import reverse

from pybb.models import Post


def test_subscription(admin_user, django_user_model, api_client, topic):
    user2 = django_user_model.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
    user3 = django_user_model.objects.create_user(username='user3', password='user3', email='user3@example.com')

    api_client.force_authenticate(user2)
    subscribe_url = reverse('pybb:add_subscription', args=[topic.id])
    response = api_client.get(subscribe_url)
    assert response.status_code == 405, 'GET requests should not change subscriptions'
    response = api_client.post(subscribe_url)
    assert response.status_code == 200

    assert user2 in topic.subscribers.all()

    topic.subscribers.add(user3)

    # create a new reply (with another user)
    api_client.force_authenticate(admin_user)
    add_post_url = reverse('pybb:add_post')
    values = {
        'topic': topic.id,
        'body': 'test subscription юникод'
    }
    response = api_client.post(add_post_url, values)
    assert response.status_code == 201
    new_post = Post.objects.get(body=values['body'])

    # there should only be one email in the outbox (to user2) because @example.com are ignored
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to[0] == user2.email
    assert all([new_post.get_absolute_url() in msg.body for msg in mail.outbox])

    # unsubscribe
    api_client.force_authenticate(user2)
    response = api_client.get(reverse('pybb:delete_subscription', args=[topic.id]))
    assert response.status_code == 405, 'Need to make a post request to unsubscribe'
    response = api_client.post(reverse('pybb:delete_subscription', args=[topic.id]))
    assert response.status_code == 200
    assert user2 not in topic.subscribers.all()


def test_subscription_disabled(settings, admin_user, django_user_model, api_client, topic):
    settings.PYBB_DISABLE_SUBSCRIPTIONS = True
    user2 = django_user_model.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
    user3 = django_user_model.objects.create_user(username='user3', password='user3', email='user3@example.com')

    api_client.force_authenticate(user2)
    subscribe_url = reverse('pybb:add_subscription', args=[topic.id])

    response = api_client.post(subscribe_url, follow=True)
    assert response.status_code == 404

    topic.subscribers.add(user3)

    # create a new reply (with another user)
    api_client.force_authenticate(admin_user)
    add_post_url = reverse('pybb:add_post')
    values = {
        'topic': topic.id,
        'body': 'test subscription юникод'
    }
    response = api_client.post(add_post_url, values)
    assert response.status_code == 201

    # there should be one email in the outbox (user3)
    # because already subscribed users will still receive notifications.
    assert len(mail.outbox) == 1
    assert mail.outbox[0].to[0] == user3.email


def test_notifications_disabled(settings, admin_user, django_user_model, topic, api_client):
    settings.PYBB_DISABLE_NOTIFICATIONS = True
    user2 = django_user_model.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
    user3 = django_user_model.objects.create_user(username='user3', password='user3', email='user3@example.com')

    api_client.force_authenticate(user2)
    subscribe_url = reverse('pybb:add_subscription', args=[topic.id])
    response = api_client.get(subscribe_url, follow=True)
    assert response.status_code == 405, 'GET requests should not change subscriptions'

    response = api_client.post(subscribe_url, follow=True)
    assert response.status_code == 200

    topic.subscribers.add(user3)

    # create a new reply (with another user)
    api_client.force_authenticate(admin_user)
    add_post_url = reverse('pybb:add_post')
    values = {
        'body': 'test subscribtion юникод',
        'topic': topic.id
    }
    response = api_client.post(add_post_url, values)
    assert response.status_code == 201

    # there should be no email in the outbox
    assert len(mail.outbox) == 0
