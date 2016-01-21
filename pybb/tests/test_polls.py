# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.test import override_settings
from lxml import html
from rest_framework.test import APITestCase

from pybb.models import Topic, PollAnswer, Category, Forum, Post, PollAnswerUser
from pybb.tests.utils import User


@override_settings(PYBB_POLL_MAX_ANSWERS=2)
class PollTest(APITestCase):

    def test_poll_add(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        add_topic_url = reverse('pybb:topic_list')
        self.client.force_authenticate(user)
        values = {
            'forum': forum.id,
            'body': 'test poll body',
            'name': 'test poll name',
            'poll_type': Topic.POLL_TYPE_NONE,
            'poll_question': 'q1',
            'poll_answers': [
                {'text': 'answer1'},
                {'text': 'answer2'}
            ]
        }
        response = self.client.post(add_topic_url, values)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Topic.objects.filter(name='test poll name').exists())

        values['name'] = 'test poll name 1'
        values['poll_type'] = Topic.POLL_TYPE_SINGLE
        values['poll_answers'] = {'text': 'answer1'}  # not enough answers
        response = self.client.post(add_topic_url, values)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Topic.objects.filter(name='test poll name 1').exists())

        values['name'] = 'test poll name 2'
        values['poll_type'] = 1
        values['poll_answers'] = [
            {'text': 'answer1'},  # too many answers
            {'text': 'answer2'},
            {'text': 'answer3'}
        ]
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Topic.objects.filter(name='test poll name 2').exists())

        values['name'] = 'test poll name 3'
        values['poll_type'] = Topic.POLL_TYPE_SINGLE
        values['poll_answers'] = [
            {'text': 'answer1'},  # two answers - what do we need to create poll
            {'text': 'answer2'}
        ]
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 201)
        new_topic = Topic.objects.get(name='test poll name 3')
        self.assertEqual(new_topic.poll_answers.first().text, 'answer1')
        self.assertEqual(PollAnswer.objects.filter(topic=new_topic).count(), 2)

    def test_attempt_to_create_poll_with_no_answers(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        add_topic_url = reverse('pybb:topic_list')
        self.client.force_authenticate(user)
        values = {
            'forum': forum.id,
            'body': 'test poll body',
            'name': 'test poll name',
            'poll_type': Topic.POLL_TYPE_SINGLE,
            'poll_question': 'q1',
            'poll_answers': []
        }
        response = self.client.post(add_topic_url, values)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(Topic.objects.filter(name='test poll name').exists())

    def test_regression_poll_deletion_after_second_post(self):
        self.login_client()

        add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': self.forum.id})
        response = self.client.get(add_topic_url)
        values = self.get_form_values(response)
        values['body'] = 'test poll body'
        values['name'] = 'test poll name'
        values['poll_type'] = 1 # poll type = single choice, create answers
        values['poll_question'] = 'q1'
        values['poll_answers-0-text'] = 'answer1' # two answers - what do we need to create poll
        values['poll_answers-1-text'] = 'answer2'
        values['poll_answers-TOTAL_FORMS'] = 2
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        new_topic = Topic.objects.get(name='test poll name')
        self.assertEqual(new_topic.poll_question, 'q1')
        self.assertEqual(PollAnswer.objects.filter(topic=new_topic).count(), 2)

        add_post_url = reverse('pybb:add_post', kwargs={'topic_id': new_topic.id})
        response = self.client.get(add_post_url)
        values = self.get_form_values(response)
        values['body'] = 'test answer body'
        response = self.client.post(add_post_url, values, follow=True)
        self.assertEqual(PollAnswer.objects.filter(topic=new_topic).count(), 2)

    def test_poll_edit(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        poll = Topic.objects.create(
            forum=forum,
            user=user,
            poll_type=Topic.POLL_TYPE_SINGLE,
            poll_question='Hows it hanging?',
        )
        for answer in ('A little to the left', 'None of your business'):
            PollAnswer.objects.create(topic=poll, text=answer)
        Post.objects.create(topic=poll, user=user, user_ip='0.0.0.0',
                            body='Head post is necessary because default edit permission check uses it')
        edit_topic_url = reverse('pybb:edit_topic', kwargs={'pk': poll.pk})
        self.client.force_authenticate(user)
        values = {
            'forum': forum.pk,
            'name': 'test poll',
            'body': 'edited head post body',
            'poll_type': Topic.POLL_TYPE_SINGLE,
            'poll_question': 'q1',
            'poll_answers': [
                {'text': 'answer1'},
                {'text': 'answer2'}
            ]
        }
        response = self.client.put(edit_topic_url, values)
        self.assertEqual(response.status_code, 200)
        poll = Topic.objects.get(id=poll.id)
        self.assertEqual(poll.poll_type, Topic.POLL_TYPE_SINGLE)
        self.assertEqual(poll.poll_question, 'q1')
        self.assertEqual(PollAnswer.objects.filter(topic=poll).count(), 2)

        values.update(**{
            'name': 'edited test poll',
            'poll_type': Topic.POLL_TYPE_MULTIPLE,
            'poll_question': 'q100',
            'poll_answers': [
                {'text': 'answer100'},
                {'text': 'answer200'}
            ]
        })
        response = self.client.put(edit_topic_url, values)
        self.assertEqual(response.status_code, 200)
        poll = Topic.objects.get(id=poll.id)
        self.assertEqual(poll.poll_type, Topic.POLL_TYPE_MULTIPLE)
        self.assertEqual(poll.poll_question, 'q100')
        answers = poll.poll_answers.all()
        self.assertEqual(len(answers), 2)
        self.assertEqual(answers[0].text, 'answer100')
        self.assertEqual(answers[1].text, 'answer200')

        values['poll_type'] = Topic.POLL_TYPE_NONE
        values.pop('poll_answers')
        values.pop('poll_question')
        response = self.client.put(edit_topic_url, values)
        self.assertEqual(response.status_code, 200)
        poll = Topic.objects.get(id=poll.id)
        self.assertEqual(poll.poll_type, Topic.POLL_TYPE_NONE)
        self.assertEqual(poll.poll_question, '')
        self.assertEqual(PollAnswer.objects.filter(topic=poll).count(), 0)

    def test_poll_voting(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        poll = Topic.objects.create(
            forum=forum,
            user=user,
            poll_type=Topic.POLL_TYPE_SINGLE,
            poll_question='Hows it hanging?',
        )
        for answer in ('A little to the left', 'None of your business'):
            PollAnswer.objects.create(topic=poll, text=answer)
        Post.objects.create(topic=poll, user=user, user_ip='0.0.0.0',
                            body='Head post is necessary because default edit permission check uses it')
        vote_url = reverse('pybb:topic_poll_vote', kwargs={'pk': poll.id})
        my_answer = PollAnswer.objects.all()[0]
        values = {'answers': [my_answer.id]}
        self.client.force_authenticate(user)
        response = self.client.post(vote_url, data=values)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Topic.objects.get(id=poll.id).poll_votes(), 1)
        poll_answer = PollAnswer.objects.get(id=my_answer.id)
        self.assertEqual(poll_answer.votes, 1)
        self.assertEqual(poll_answer.votes_percent, 100.0)

        # already voted
        response = self.client.post(vote_url, data=values)
        self.assertEqual(response.status_code, 403)  # bad request status

        poll.poll_type = Topic.POLL_TYPE_MULTIPLE
        poll.save()
        PollAnswerUser.objects.filter(user=user).delete()
        values = {'answers': [a.id for a in PollAnswer.objects.all()]}
        response = self.client.post(vote_url, data=values)
        self.assertEqual(response.status_code, 200)
        poll_answers = PollAnswer.objects.all()
        self.assertListEqual([a.votes for a in poll_answers], [1, 1])
        self.assertListEqual([a.votes_percent for a in poll_answers], [50.0, 50.0])

        response = self.client.post(vote_url, data=values)
        self.assertEqual(response.status_code, 403)  # already voted

        cancel_vote_url = reverse('pybb:topic_cancel_poll_vote', kwargs={'pk': poll.id})
        response = self.client.post(cancel_vote_url, data=values)
        self.assertEqual(response.status_code, 200)
        poll_answers = PollAnswer.objects.all()
        self.assertListEqual([a.votes for a in poll_answers], [0, 0])
        self.assertListEqual([a.votes_percent for a in poll_answers], [0, 0])

        response = self.client.post(vote_url, data=values)
        self.assertEqual(response.status_code, 200)
        poll_answers = PollAnswer.objects.all()
        self.assertListEqual([a.votes for a in poll_answers], [1, 1])
        self.assertListEqual([a.votes_percent for a in poll_answers], [50.0, 50.0])

    def test_poll_voting_on_closed_topic(self):
        category = Category.objects.create(name='foo')
        forum = Forum.objects.create(name='xfoo', description='bar', category=category)
        user = User.objects.create_user('zeus', 'zeus@localhost', 'zeus')
        poll = Topic.objects.create(
            forum=forum,
            user=user,
            poll_type=Topic.POLL_TYPE_SINGLE,
            poll_question='Hows it hanging?',
        )
        Post.objects.create(topic=poll, user=user, user_ip='0.0.0.0',
                            body='Head post is necessary because default edit permission check uses it')
        PollAnswer.objects.create(topic=poll, text='answer1')
        PollAnswer.objects.create(topic=poll, text='answer2')
        poll.closed = True
        poll.save()

        vote_url = reverse('pybb:topic_poll_vote', kwargs={'pk': poll.id})
        my_answer = PollAnswer.objects.all()[0]
        values = {'answers': my_answer.id}
        self.client.force_authenticate(user)
        response = self.client.post(vote_url, data=values)
        self.assertEqual(response.status_code, 403)

    def login_client(self, username='zeus', password='zeus'):
        self.client.login(username=username, password=password)

    def create_initial(self, post=True):
        self.category = Category.objects.create(name='foo')
        self.forum = Forum.objects.create(name='xfoo', description='bar', category=self.category)
        self.topic = Topic.objects.create(name='etopic', forum=self.forum, user=self.user)
        if post:
            self.post = Post.objects.create(topic=self.topic, user=self.user, body='bbcode [b]test[/b]', user_ip='0.0.0.0')

    def get_form_values(self, response, form="post-form"):
        return dict(html.fromstring(response.content).xpath('//form[@class="%s"]' % form)[0].form_values())

    def get_with_user(self, url, username=None, password=None):
        if username:
            self.client.login(username=username, password=password)
        r = self.client.get(url)
        self.client.logout()
        return r
