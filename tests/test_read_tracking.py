from django.core.urlresolvers import reverse
from django.utils.timezone import now
from rest_framework.test import APIClient

from pybb.models import Post, Topic, TopicReadTracker, ForumReadTracker
from pybb.read_tracking import get_read_topic_trackers, get_unread_topics_in_forum
from pybb.templatetags.pybb_tags import pybb_topic_unread


def test_get_read_topic_trackers(user, forum, django_user_model, precision_time):
    for i in range(3):
        t = Topic.objects.create(forum=forum, name='test topic {}'.format(i), user=user)
        Post.objects.create(topic=t, user=user, user_ip='0.0.0.0', body='Topics need a post')

    other_user = django_user_model.objects.create_user('two', 'two@localhost', 'two')
    assert not get_read_topic_trackers(other_user, forum).exists()

    for t in forum.topics.all():
        TopicReadTracker.objects.create(user=other_user, topic=t, time_stamp=now())

    assert get_read_topic_trackers(other_user, forum).count() == forum.topics.count()


def test_get_unread_topics_in_forum(user, forum, django_user_model, precision_time):
    for i in range(3):
        t = Topic.objects.create(forum=forum, name='test topic {}'.format(i), user=user)
        Post.objects.create(topic=t, user=user, user_ip='0.0.0.0', body='Topics need a post')

    other_user = django_user_model.objects.create_user('two', 'two@localhost', 'two')
    assert get_unread_topics_in_forum(other_user, forum).count() == 3

    topic = forum.topics.last()
    TopicReadTracker.objects.create(user=other_user, topic=topic, time_stamp=now())

    assert get_unread_topics_in_forum(other_user, forum).count() == 2

    Post.objects.create(topic=topic, user=user, user_ip='0.0.0.0', body='New update in topic')
    assert get_unread_topics_in_forum(other_user, forum).count() == 3


def test_get_unread_topics_in_forum_with_forum_read_tracker(user, forum, django_user_model, precision_time):
    for i in range(3):
        t = Topic.objects.create(forum=forum, name='test topic {}'.format(i), user=user)
        Post.objects.create(topic=t, user=user, user_ip='0.0.0.0', body='Topics need a post')

    other_user = django_user_model.objects.create_user('two', 'two@localhost', 'two')
    assert get_unread_topics_in_forum(other_user, forum).count() == 3

    ForumReadTracker.objects.create(user=other_user, forum=forum, time_stamp=now())
    assert get_unread_topics_in_forum(other_user, forum).count() == 0

    Post.objects.create(topic=forum.topics.first(), user=user, user_ip='0.0.0.0', body='New update in topic')
    assert get_unread_topics_in_forum(other_user, forum).count() == 1


def test_read_tracking(user, topic, api_client, admin_user, precision_time):
    Topic.objects.create(forum=topic.forum, name='other topic', user=admin_user)
    for t in Topic.objects.all():
        Post.objects.create(topic=t, user=admin_user, user_ip='0.0.0.0', body='Topics need a post')

    api_client.force_authenticate(user)
    # Forum status
    response = api_client.get(topic.forum.get_absolute_url())
    assert response.status_code == 200
    assert response.data['unread']
    response = api_client.get(reverse('pybb:forum_list'))
    assert response.data['results'][0]['unread']

    # Topic status
    response = api_client.get(topic.get_absolute_url())
    assert response.status_code == 200
    assert response.data['unread']
    response = api_client.get(reverse('pybb:topic_list'), {'forum': topic.forum.id})
    assert response.data['results'][0]['unread']

    # Read the posts
    post_list_url = reverse('pybb:post_list')
    api_client.get(post_list_url, {'topic': topic.id})
    # Topic status - read
    response = api_client.get(topic.get_absolute_url())
    assert not response.data['unread']
    # Forum status - read
    response = api_client.get(topic.forum.get_absolute_url())
    assert response.data['unread']
    # Visit others
    for t in topic.forum.topics.all():
        api_client.get(post_list_url, {'topic': t.id})
    # Forum status - read
    response = api_client.get(topic.forum.get_absolute_url())
    assert not response.data['unread']


def test_adding_post_marks_as_read(user, topic, api_client, precision_time):
    add_post_url = reverse('pybb:post_list')
    values = {
        'topic': topic.id,
        'body': 'test tracking'
    }
    api_client.force_authenticate(user)
    response = api_client.post(add_post_url, values)
    assert response.status_code == 201
    assert response.data['body'] == 'test tracking'
    # Topic status - readed
    response = api_client.get(topic.get_absolute_url())
    assert not response.data['unread']
    # Forum status - readed
    response = api_client.get(topic.forum.get_absolute_url())
    assert not response.data['unread']


def test_mark_all_as_read(user, topic, api_client, precision_time):
    assert get_unread_topics_in_forum(user, topic.forum).count() == 1

    api_client.force_authenticate(user)
    response = api_client.get(reverse('pybb:mark_all_as_read'))
    assert response.status_code == 405
    response = api_client.post(reverse('pybb:mark_all_as_read'))
    assert response.status_code == 200

    assert get_unread_topics_in_forum(user, topic.forum).count() == 0


def test_read_tracking_multi_user(user, topic, django_user_model, precision_time):
    forum = topic.forum
    topic_2 = Topic.objects.create(name='topic_2', forum=forum, user=user)
    Post.objects.create(topic=topic_2, user=user, body='one', user_ip='0.0.0.0')

    user_alice = django_user_model.objects.create_user('alice', 'alice@localhost', 'alice')
    client_alice = APIClient()
    client_alice.force_authenticate(user_alice)

    user_bob = django_user_model.objects.create_user('bob', 'bob@localhost', 'bob')
    client_bob = APIClient()
    client_bob.force_authenticate(user_bob)

    # Two topics, each with one post. everything is unread, so the db should reflect that:
    assert TopicReadTracker.objects.count() == 0
    assert ForumReadTracker.objects.count() == 0

    # user_alice reads topic_1, she should get one topic read tracker, there should be no forum read trackers
    client_alice.get(topic.get_absolute_url())
    assert TopicReadTracker.objects.all().count() == 1
    assert TopicReadTracker.objects.filter(user=user_alice).count() == 1
    assert TopicReadTracker.objects.filter(user=user_alice, topic=topic).count() == 1
    assert ForumReadTracker.objects.all().count() == 0

    # user_bob reads topic, he should get one topic read tracker, there should be no forum read trackers
    client_bob.get(topic.get_absolute_url())
    assert TopicReadTracker.objects.all().count() == 2
    assert TopicReadTracker.objects.filter(user=user_bob).count() == 1
    assert TopicReadTracker.objects.filter(user=user_bob, topic=topic).count() == 1

    # user_bob reads topic_2, he should get a forum read tracker,
    #  there should be no topic read trackers for user_bob
    client_bob.get(topic_2.get_absolute_url())
    assert TopicReadTracker.objects.all().count() == 1
    assert ForumReadTracker.objects.all().count() == 1
    assert ForumReadTracker.objects.filter(user=user_bob).count() == 1
    assert ForumReadTracker.objects.filter(user=user_bob, forum=forum).count() == 1
    assert TopicReadTracker.objects.filter(user=user_bob).count() == 0
    for item in (t.unread for t in pybb_topic_unread([topic, topic_2], user_bob)):
        assert not item

    # user_alice creates topic_3, they should get a new topic read tracker in the db
    add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': forum.id})
    values = {
        'body': 'topic_3',
        'name': 'topic_3',
        'poll_type': 0
    }
    client_alice.post(add_topic_url, data=values, follow=True)
    assert TopicReadTracker.objects.all().count() == 2
    assert TopicReadTracker.objects.filter(user=user_alice).count() == 2
    assert ForumReadTracker.objects.all().count() == 1
    topic_3 = Topic.objects.order_by('-posts__updated', '-id')[0]
    assert topic_3.name == 'topic_3'

    # user_alice posts to topic, a topic they've already read, no new trackers should be created
    add_post_url = reverse('pybb:post_list', kwargs={'topic_id': topic.id})
    values = {
        'body': 'test tracking'
    }
    client_alice.post(add_post_url, values, follow=True)
    assert TopicReadTracker.objects.all().count() == 2
    assert TopicReadTracker.objects.filter(user=user_alice).count() == 2
    assert ForumReadTracker.objects.all().count() == 1

    # user_bob has two unread topics, 'topic' and 'topic_3'.
    #   This is because user_alice created a new topic and posted to an existing topic,
    #   after user_bob got his forum read tracker.

    # user_bob reads 'topic'
    #   user_bob gets a new topic read tracker, and the existing forum read tracker stays the same.
    #   'topic_3' appears unread for user_bob
    #
    previous_time = ForumReadTracker.objects.all()[0].time_stamp
    client_bob.get(topic.get_absolute_url())
    assert ForumReadTracker.objects.all().count() == 1
    assert ForumReadTracker.objects.all()[0].time_stamp == previous_time
    assert TopicReadTracker.objects.filter(user=user_bob).count() == 1
    assert TopicReadTracker.objects.filter(user=user_alice).count() == 2
    assert TopicReadTracker.objects.all().count() == 3

    # user_bob reads the last unread topic, 'topic_3'.
    # user_bob's existing forum read tracker updates and his topic read tracker disappears
    #
    previous_time = ForumReadTracker.objects.all()[0].time_stamp
    client_bob.get(topic_3.get_absolute_url())
    assert ForumReadTracker.objects.all().count() == 1
    assert ForumReadTracker.objects.all()[0].time_stamp > previous_time
    assert TopicReadTracker.objects.all().count() == 2
    assert TopicReadTracker.objects.filter(user=user_bob).count() == 0

# def test_read_tracking_multi_forum(self):
#     user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
#     category = Category.objects.create(name='foo')
#     forum = Forum.objects.create(name='xfoo', description='bar', category=category)
#     topic_1 = Topic.objects.create(name='xtopic', forum=forum, user=user)
#     topic_2 = Topic.objects.create(name='topic_2', forum=forum, user=user)
#
#     Post.objects.create(topic=topic_2, user=user, body='one', user_ip='0.0.0.0')
#
#     forum_2 = Forum(name='forum_2', description='bar', category=self.category)
#     forum_2.save()
#
#     Topic(name='garbage', forum=forum_2, user=user).save()
#
#     client = Client()
#     client.login(username='zeus', password='zeus')
#
#     # everything starts unread
#     self.assertEqual(ForumReadTracker.objects.all().count(), 0)
#     self.assertEqual(TopicReadTracker.objects.all().count(), 0)
#
#     # user reads topic_1, they should get one topic read tracker, there should be no forum read trackers
#     client.get(topic_1.get_absolute_url())
#     self.assertEqual(TopicReadTracker.objects.all().count(), 1)
#     self.assertEqual(TopicReadTracker.objects.filter(user=self.user).count(), 1)
#     self.assertEqual(TopicReadTracker.objects.filter(user=self.user, topic=topic_1).count(), 1)
#
#     # user reads topic_2, they should get a forum read tracker,
#     #  there should be no topic read trackers for the user
#     client.get(topic_2.get_absolute_url())
#     self.assertEqual(TopicReadTracker.objects.all().count(), 0)
#     self.assertEqual(ForumReadTracker.objects.all().count(), 1)
#     self.assertEqual(ForumReadTracker.objects.filter(user=user).count(), 1)
#     self.assertEqual(ForumReadTracker.objects.filter(user=user, forum=forum).count(), 1)
#
# def test_read_tracker_after_posting(self):
#     user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
#     category = Category.objects.create(name='foo')
#     forum = Forum.objects.create(name='xfoo', description='bar', category=category)
#     topic = Topic.objects.create(name='xtopic', forum=forum, user=user)
#     client = Client()
#     client.login(username='zeus', password='zeus')
#     add_post_url = reverse('pybb:post_list', kwargs={'topic_id': topic.id})
#     response = client.get(add_post_url)
#     values = self.get_form_values(response)
#     values['body'] = 'test tracking'
#     response = client.post(add_post_url, values, follow=True)
#
#     # after posting in topic it should be readed
#     # because there is only one topic, so whole forum should be marked as readed
#     self.assertEqual(TopicReadTracker.objects.filter(user=user, topic=topic).count(), 0)
#     self.assertEqual(ForumReadTracker.objects.filter(user=user, forum=forum).count(), 1)
#
# def test_pybb_is_topic_unread_filter(self):
#     user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
#     category = Category.objects.create(name='foo')
#     forum = Forum.objects.create(name='xfoo', description='bar', category=category)
#     topic_1 = Topic.objects.create(name='xtopic', forum=forum, user=user)
#     topic_2 = Topic.objects.create(name='topic_2', forum=forum, user=user)
#
#     forum_2 = Forum.objects.create(name='forum_2', description='forum2', category=category)
#     topic_3 = Topic.objects.create(name='topic_2', forum=forum_2, user=user)
#
#     Post.objects.create(topic=topic_1, user=user, body='one', user_ip='0.0.0.0').save()
#     Post.objects.create(topic=topic_2, user=user, body='two', user_ip='0.0.0.0').save()
#     Post.objects.create(topic=topic_3, user=user, body='three', user_ip='0.0.0.0').save()
#
#     user_alice = User.objects.create_user('alice', 'alice@localhost', 'alice')
#     client_alice = Client()
#     client_alice.login(username='alice', password='alice')
#
#     # Two topics, each with one post. everything is unread, so the db should reflect that:
#     self.assertTrue(pybb_is_topic_unread(topic_1, user_alice))
#     self.assertTrue(pybb_is_topic_unread(topic_2, user_alice))
#     self.assertTrue(pybb_is_topic_unread(topic_3, user_alice))
#     self.assertListEqual(
#         [t.unread for t in pybb_topic_unread([topic_1, topic_2, topic_3], user_alice)],
#         [True, True, True])
#
#     client_alice.get(topic_1.get_absolute_url())
#     topic_1 = Topic.objects.get(id=topic_1.id)
#     topic_2 = Topic.objects.get(id=topic_2.id)
#     topic_3 = Topic.objects.get(id=topic_3.id)
#     self.assertFalse(pybb_is_topic_unread(topic_1, user_alice))
#     self.assertTrue(pybb_is_topic_unread(topic_2, user_alice))
#     self.assertTrue(pybb_is_topic_unread(topic_3, user_alice))
#     self.assertListEqual(
#         [t.unread for t in pybb_topic_unread([topic_1, topic_2, topic_3], user_alice)],
#         [False, True, True])
#
#     client_alice.get(topic_2.get_absolute_url())
#     topic_1 = Topic.objects.get(id=topic_1.id)
#     topic_2 = Topic.objects.get(id=topic_2.id)
#     topic_3 = Topic.objects.get(id=topic_3.id)
#     self.assertFalse(pybb_is_topic_unread(topic_1, user_alice))
#     self.assertFalse(pybb_is_topic_unread(topic_2, user_alice))
#     self.assertTrue(pybb_is_topic_unread(topic_3, user_alice))
#     self.assertListEqual(
#         [t.unread for t in pybb_topic_unread([topic_1, topic_2, topic_3], user_alice)],
#         [False, False, True])
#
#     client_alice.get(topic_3.get_absolute_url())
#     topic_1 = Topic.objects.get(id=topic_1.id)
#     topic_2 = Topic.objects.get(id=topic_2.id)
#     topic_3 = Topic.objects.get(id=topic_3.id)
#     self.assertFalse(pybb_is_topic_unread(topic_1, user_alice))
#     self.assertFalse(pybb_is_topic_unread(topic_2, user_alice))
#     self.assertFalse(pybb_is_topic_unread(topic_3, user_alice))
#     self.assertListEqual(
#         [t.unread for t in pybb_topic_unread([topic_1, topic_2, topic_3], user_alice)],
#         [False, False, False])
#
# def test_is_forum_unread_filter(self):
#     user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
#     category = Category.objects.create(name='foo')
#
#     forum_parent = Forum.objects.create(name='f1', category=category)
#     forum_child1 = Forum.objects.create(name='f2', category=category, parent=forum_parent)
#     forum_child2 = Forum.objects.create(name='f3', category=category, parent=forum_parent)
#     topic_1 = Topic.objects.create(name='topic_1', forum=forum_parent, user=user)
#     topic_2 = Topic.objects.create(name='topic_2', forum=forum_child1, user=user)
#     topic_3 = Topic.objects.create(name='topic_3', forum=forum_child2, user=user)
#
#     Post.objects.create(topic=topic_1, user=user, body='one', user_ip='0.0.0.0')
#     Post.objects.create(topic=topic_2, user=user, body='two', user_ip='0.0.0.0')
#     Post.objects.create(topic=topic_3, user=user, body='three', user_ip='0.0.0.0')
#
#     user_alice = User.objects.create_user('alice', 'alice@localhost', 'alice')
#     client_alice = Client()
#     client_alice.login(username='alice', password='alice')
#
#     forum_parent = Forum.objects.get(id=forum_parent.id)
#     forum_child1 = Forum.objects.get(id=forum_child1.id)
#     forum_child2 = Forum.objects.get(id=forum_child2.id)
#     self.assertListEqual([f.unread for f in pybb_forum_unread([forum_parent, forum_child1, forum_child2], user_alice)],
#                          [True, True, True])
#
#     # unless we read parent topic, there is unreaded topics in child forums
#     client_alice.get(topic_1.get_absolute_url())
#     forum_parent = Forum.objects.get(id=forum_parent.id)
#     forum_child1 = Forum.objects.get(id=forum_child1.id)
#     forum_child2 = Forum.objects.get(id=forum_child2.id)
#     self.assertListEqual([f.unread for f in pybb_forum_unread([forum_parent, forum_child1, forum_child2], user_alice)],
#                          [True, True, True])
#
#     # still unreaded topic in one of the child forums
#     client_alice.get(topic_2.get_absolute_url())
#     forum_parent = Forum.objects.get(id=forum_parent.id)
#     forum_child1 = Forum.objects.get(id=forum_child1.id)
#     forum_child2 = Forum.objects.get(id=forum_child2.id)
#     self.assertListEqual([f.unread for f in pybb_forum_unread([forum_parent, forum_child1, forum_child2], user_alice)],
#                          [True, False, True])
#
#     # all topics readed
#     client_alice.get(topic_3.get_absolute_url())
#     forum_parent = Forum.objects.get(id=forum_parent.id)
#     forum_child1 = Forum.objects.get(id=forum_child1.id)
#     forum_child2 = Forum.objects.get(id=forum_child2.id)
#     self.assertListEqual([f.unread for f in pybb_forum_unread([forum_parent, forum_child1, forum_child2], user_alice)],
#                          [False, False, False])
#
# @skipUnlessDBFeature('supports_microsecond_precision')
# def test_read_tracker_when_topics_forum_changed(self):
#     user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
#     category = Category.objects.create(name='foo')
#     forum_1 = Forum.objects.create(name='f1', description='bar', category=category)
#     forum_2 = Forum.objects.create(name='f2', description='bar', category=category)
#     topic_1 = Topic.objects.create(name='t1', forum=forum_1, user=user)
#     topic_2 = Topic.objects.create(name='t2', forum=forum_2, user=user)
#
#     Post.objects.create(topic=topic_1, user=user, body='one', user_ip='0.0.0.0')
#     Post.objects.create(topic=topic_2, user=user, body='two', user_ip='0.0.0.0')
#
#     user_alice = User.objects.create_user('alice', 'alice@localhost', 'alice')
#     client_alice = Client()
#     client_alice.login(username='alice', password='alice')
#
#     # Everything is unread
#     self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_alice)], [True, True])
#     self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_alice)], [True, True])
#
#     # read all
#     client_alice.get(reverse('pybb:mark_all_as_read'))
#     self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_alice)], [False, False])
#     self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_alice)], [False, False])
#
#     post = Post.objects.create(topic=topic_1, user=user, body='three', user_ip='0.0.0.0')
#     post = Post.objects.get(id=post.id)  # get post with timestamp from DB
#
#     topic_1 = Topic.objects.get(id=topic_1.id)
#     topic_2 = Topic.objects.get(id=topic_2.id)
#     self.assertAlmostEqual(topic_1.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
#     self.assertAlmostEqual(forum_1.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
#     self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_alice)], [True, False])
#     self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_alice)], [True, False])
#
#     post.topic = topic_2
#     post.save()
#     topic_1 = Topic.objects.get(id=topic_1.id)
#     topic_2 = Topic.objects.get(id=topic_2.id)
#     forum_1 = Forum.objects.get(id=forum_1.id)
#     forum_2 = Forum.objects.get(id=forum_2.id)
#     self.assertAlmostEqual(topic_2.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
#     self.assertAlmostEqual(forum_2.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
#     self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_alice)], [False, True])
#     self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_alice)], [False, True])
#
#     topic_2.forum = forum_1
#     topic_2.save()
#     topic_1 = Topic.objects.get(id=topic_1.id)
#     topic_2 = Topic.objects.get(id=topic_2.id)
#     forum_1 = Forum.objects.get(id=forum_1.id)
#     forum_2 = Forum.objects.get(id=forum_2.id)
#     self.assertAlmostEqual(forum_1.updated, post.updated or post.created, delta=datetime.timedelta(milliseconds=50))
#     self.assertListEqual([t.unread for t in pybb_topic_unread([topic_1, topic_2], user_alice)], [False, True])
#     self.assertListEqual([t.unread for t in pybb_forum_unread([forum_1, forum_2], user_alice)], [True, False])
#
# @skipUnlessDBFeature('supports_microsecond_precision')
# def test_open_first_unread_post(self):
#     user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
#     category = Category.objects.create(name='foo')
#     forum_1 = Forum.objects.create(category=category, name='foo')
#     topic_1 = Topic.objects.create(name='topic_1', forum=forum_1, user=user)
#     topic_2 = Topic.objects.create(name='topic_2', forum=forum_1, user=user)
#
#     post_1_1 = Post.objects.create(topic=topic_1, user=user, body='1_1', user_ip='0.0.0.0')
#     post_1_2 = Post.objects.create(topic=topic_1, user=user, body='1_2', user_ip='0.0.0.0')
#     post_2_1 = Post.objects.create(topic=topic_2, user=user, body='2_1', user_ip='0.0.0.0')
#
#     user_alice = User.objects.create_user('alice', 'alice@localhost', 'alice')
#     client_alice = Client()
#     client_alice.login(username='alice', password='alice')
#
#     response = client_alice.get(topic_1.get_absolute_url(), data={'first-unread': 1}, follow=True)
#     self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_1.get_absolute_url(), 1, post_1_1.id))
#
#     response = client_alice.get(topic_1.get_absolute_url(), data={'first-unread': 1}, follow=True)
#     self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_1.get_absolute_url(), 1, post_1_2.id))
#
#     response = client_alice.get(topic_2.get_absolute_url(), data={'first-unread': 1}, follow=True)
#     self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_2.get_absolute_url(), 1, post_2_1.id))
#
#     post_1_3 = Post.objects.create(topic=topic_1, user=user, body='1_3', user_ip='0.0.0.0')
#     post_1_4 = Post.objects.create(topic=topic_1, user=user, body='1_4', user_ip='0.0.0.0')
#
#     response = client_alice.get(topic_1.get_absolute_url(), data={'first-unread': 1}, follow=True)
#     self.assertRedirects(response, '%s?page=%d#post-%d' % (topic_1.get_absolute_url(), 1, post_1_3.id))
