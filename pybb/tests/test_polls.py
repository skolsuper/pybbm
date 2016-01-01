# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.core.urlresolvers import reverse
from django.test import TestCase

from pybb.models import Topic, PollAnswer
from pybb.settings import settings as pybb_settings
from pybb.tests.utils import SharedTestModule


class PollTest(TestCase, SharedTestModule):
    def setUp(self):
        self.create_user()
        self.create_initial()
        self.PYBB_POLL_MAX_ANSWERS = pybb_settings.PYBB_POLL_MAX_ANSWERS
        pybb_settings.PYBB_POLL_MAX_ANSWERS = 2

    def test_poll_add(self):
        add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': self.forum.id})
        self.login_client()
        response = self.client.get(add_topic_url)
        values = self.get_form_values(response)
        values['body'] = 'test poll body'
        values['name'] = 'test poll name'
        values['poll_type'] = 0 # poll_type = None, create topic without poll answers
        values['poll_question'] = 'q1'
        values['poll_answers-0-text'] = 'answer1'
        values['poll_answers-1-text'] = 'answer2'
        values['poll_answers-TOTAL_FORMS'] = 2
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        new_topic = Topic.objects.get(name='test poll name')
        self.assertIsNone(new_topic.poll_question)
        self.assertFalse(PollAnswer.objects.filter(topic=new_topic).exists()) # no answers here

        values['name'] = 'test poll name 1'
        values['poll_type'] = 1
        values['poll_answers-0-text'] = 'answer1' # not enough answers
        values['poll_answers-TOTAL_FORMS'] = 1
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertFalse(Topic.objects.filter(name='test poll name 1').exists())

        values['name'] = 'test poll name 1'
        values['poll_type'] = 1
        values['poll_answers-0-text'] = 'answer1' # too many answers
        values['poll_answers-1-text'] = 'answer2'
        values['poll_answers-2-text'] = 'answer3'
        values['poll_answers-TOTAL_FORMS'] = 3
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertFalse(Topic.objects.filter(name='test poll name 1').exists())

        values['name'] = 'test poll name 1'
        values['poll_type'] = 1 # poll type = single choice, create answers
        values['poll_question'] = 'q1'
        values['poll_answers-0-text'] = 'answer1' # two answers - what do we need to create poll
        values['poll_answers-1-text'] = 'answer2'
        values['poll_answers-TOTAL_FORMS'] = 2
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        new_topic = Topic.objects.get(name='test poll name 1')
        self.assertEqual(new_topic.poll_question, 'q1')
        self.assertEqual(PollAnswer.objects.filter(topic=new_topic).count(), 2)

    def test_regression_adding_poll_with_removed_answers(self):
        add_topic_url = reverse('pybb:add_topic', kwargs={'forum_id': self.forum.id})
        self.login_client()
        response = self.client.get(add_topic_url)
        values = self.get_form_values(response)
        values['body'] = 'test poll body'
        values['name'] = 'test poll name'
        values['poll_type'] = 1
        values['poll_question'] = 'q1'
        values['poll_answers-0-text'] = ''
        values['poll_answers-0-DELETE'] = 'on'
        values['poll_answers-1-text'] = ''
        values['poll_answers-1-DELETE'] = 'on'
        values['poll_answers-TOTAL_FORMS'] = 2
        response = self.client.post(add_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
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
        edit_topic_url = reverse('pybb:edit_post', kwargs={'pk': self.post.id})
        self.login_client()
        response = self.client.get(edit_topic_url)
        values = self.get_form_values(response)
        values['poll_type'] = 1 # add_poll
        values['poll_question'] = 'q1'
        values['poll_answers-0-text'] = 'answer1'
        values['poll_answers-1-text'] = 'answer2'
        values['poll_answers-TOTAL_FORMS'] = 2
        response = self.client.post(edit_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Topic.objects.get(id=self.topic.id).poll_type, 1)
        self.assertEqual(Topic.objects.get(id=self.topic.id).poll_question, 'q1')
        self.assertEqual(PollAnswer.objects.filter(topic=self.topic).count(), 2)

        values = self.get_form_values(self.client.get(edit_topic_url))
        values['poll_type'] = 2 # change_poll type
        values['poll_question'] = 'q100' # change poll question
        values['poll_answers-0-text'] = 'answer100' # change poll answers
        values['poll_answers-1-text'] = 'answer200'
        values['poll_answers-TOTAL_FORMS'] = 2
        response = self.client.post(edit_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Topic.objects.get(id=self.topic.id).poll_type, 2)
        self.assertEqual(Topic.objects.get(id=self.topic.id).poll_question, 'q100')
        self.assertEqual(PollAnswer.objects.filter(topic=self.topic).count(), 2)
        self.assertTrue(PollAnswer.objects.filter(text='answer100').exists())
        self.assertTrue(PollAnswer.objects.filter(text='answer200').exists())
        self.assertFalse(PollAnswer.objects.filter(text='answer1').exists())
        self.assertFalse(PollAnswer.objects.filter(text='answer2').exists())

        values['poll_type'] = 0 # remove poll
        values['poll_answers-0-text'] = 'answer100' # no matter how many answers we provide
        values['poll_answers-TOTAL_FORMS'] = 1
        response = self.client.post(edit_topic_url, values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Topic.objects.get(id=self.topic.id).poll_type, 0)
        self.assertIsNone(Topic.objects.get(id=self.topic.id).poll_question)
        self.assertEqual(PollAnswer.objects.filter(topic=self.topic).count(), 0)

    def test_poll_voting(self):
        def recreate_poll(poll_type):
            self.topic.poll_type = poll_type
            self.topic.save()
            PollAnswer.objects.filter(topic=self.topic).delete()
            PollAnswer.objects.create(topic=self.topic, text='answer1')
            PollAnswer.objects.create(topic=self.topic, text='answer2')

        self.login_client()
        recreate_poll(poll_type=Topic.POLL_TYPE_SINGLE)
        vote_url = reverse('pybb:topic_poll_vote', kwargs={'pk': self.topic.id})
        my_answer = PollAnswer.objects.all()[0]
        values = {'answers': my_answer.id}
        response = self.client.post(vote_url, data=values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Topic.objects.get(id=self.topic.id).poll_votes(), 1)
        self.assertEqual(PollAnswer.objects.get(id=my_answer.id).votes(), 1)
        self.assertEqual(PollAnswer.objects.get(id=my_answer.id).votes_percent(), 100.0)

        # already voted
        response = self.client.post(vote_url, data=values, follow=True)
        self.assertEqual(response.status_code, 403) # bad request status

        recreate_poll(poll_type=Topic.POLL_TYPE_MULTIPLE)
        values = {'answers': [a.id for a in PollAnswer.objects.all()]}
        response = self.client.post(vote_url, data=values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual([a.votes() for a in PollAnswer.objects.all()], [1, 1])
        self.assertListEqual([a.votes_percent() for a in PollAnswer.objects.all()], [50.0, 50.0])

        response = self.client.post(vote_url, data=values, follow=True)
        self.assertEqual(response.status_code, 403)  # already voted

        cancel_vote_url = reverse('pybb:topic_cancel_poll_vote', kwargs={'pk': self.topic.id})
        response = self.client.post(cancel_vote_url, data=values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual([a.votes() for a in PollAnswer.objects.all()], [0, 0])
        self.assertListEqual([a.votes_percent() for a in PollAnswer.objects.all()], [0, 0])

        response = self.client.post(vote_url, data=values, follow=True)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual([a.votes() for a in PollAnswer.objects.all()], [1, 1])
        self.assertListEqual([a.votes_percent() for a in PollAnswer.objects.all()], [50.0, 50.0])

    def test_poll_voting_on_closed_topic(self):
        self.login_client()
        self.topic.poll_type = Topic.POLL_TYPE_SINGLE
        self.topic.save()
        PollAnswer.objects.create(topic=self.topic, text='answer1')
        PollAnswer.objects.create(topic=self.topic, text='answer2')
        self.topic.closed = True
        self.topic.save()

        vote_url = reverse('pybb:topic_poll_vote', kwargs={'pk': self.topic.id})
        my_answer = PollAnswer.objects.all()[0]
        values = {'answers': my_answer.id}
        response = self.client.post(vote_url, data=values, follow=True)
        self.assertEqual(response.status_code, 403)

    def tearDown(self):
        pybb_settings.PYBB_POLL_MAX_ANSWERS = self.PYBB_POLL_MAX_ANSWERS
