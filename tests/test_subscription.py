# coding=utf-8
from __future__ import unicode_literals

from django.core import mail
from django.core.urlresolvers import reverse

from pybb.models import Post


def test_subscription(admin_user, django_user_model, api_client, topic):
    user2 = django_user_model.objects.create_user(username='user2', password='user2', email='user2@hotmail.com')
    user3 = django_user_model.objects.create_user(username='user3', password='user3', email='user3@gmail.com')
    Post.objects.create(topic=topic, user=admin_user, user_ip='0.0.0.0', body='A first post is needed')
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
    add_post_url = reverse('pybb:post_list')
    values = {
        'topic': topic.id,
        'body': 'test subscription юникод'
    }
    response = api_client.post(add_post_url, values)
    assert response.status_code == 201
    new_post = Post.objects.get(body=values['body'])

    assert len(mail.outbox) == 2
    assert mail.outbox[0].to[0] == user2.email
    assert all([new_post.get_absolute_url() in msg.body for msg in mail.outbox])


def test_unsubscribe(api_client, user, topic):
    topic.subscribers.add(user)
    assert user in topic.subscribers.all()

    # unsubscribe
    api_client.force_authenticate(user)
    response = api_client.get(reverse('pybb:delete_subscription', args=[topic.id]))
    assert response.status_code == 405, 'Need to make a post request to unsubscribe'
    response = api_client.post(reverse('pybb:delete_subscription', args=[topic.id]))
    assert response.status_code == 200
    assert user not in topic.subscribers.all()


def test_subscription_disabled(settings, admin_user, django_user_model, api_client, topic):
    settings.PYBB_DISABLE_SUBSCRIPTIONS = True
    Post.objects.create(topic=topic, user=admin_user, user_ip='0.0.0.0', body='A first post is needed')

    user2 = django_user_model.objects.create_user(username='user2', password='user2', email='user2@someserver.com')
    user3 = django_user_model.objects.create_user(username='user3', password='user3', email='user3@example.com')
    topic.subscribers.add(user3)

    api_client.force_authenticate(user2)
    subscribe_url = reverse('pybb:add_subscription', args=[topic.id])
    response = api_client.post(subscribe_url, follow=True)
    assert response.status_code == 404

    # create a new reply (with another user)
    api_client.force_authenticate(admin_user)
    add_post_url = reverse('pybb:post_list')
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
    add_post_url = reverse('pybb:post_list')
    values = {
        'body': 'test subscribtion юникод',
        'topic': topic.id
    }
    response = api_client.post(add_post_url, values)
    assert response.status_code == 201

    # there should be no email in the outbox
    assert len(mail.outbox) == 0
