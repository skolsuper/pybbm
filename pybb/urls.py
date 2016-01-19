# -*- coding: utf-8 -*-

from __future__ import unicode_literals

from django.conf.urls import url

from pybb.feeds import LastPosts, LastTopics
from pybb.views import CategoryList, CategoryView, ForumView, TopicView,\
    CreatePostView, UpdatePostView, UserView, PostView, ProfileEditView,\
    DeletePostView, StickTopicView, UnstickTopicView, CloseTopicView,\
    OpenTopicView, moderate_post, TopicPollVoteView, ListCreateTopicsView,\
    UserTopics, UserPosts, topic_cancel_poll_vote, block_user, unblock_user,\
    delete_subscription, add_subscription, mark_all_as_read, preview_post, UpdateTopicView

urlpatterns = [
    # Syndication feeds
    url('^feeds/posts/$', LastPosts(), name='feed_posts'),
    url('^feeds/topics/$', LastTopics(), name='feed_topics'),
    # Index, Category, Forum
    url('^$', CategoryList.as_view(), name='index'),
    url('^category/(?P<pk>\d+)/$', CategoryView.as_view(), name='category'),
    url('^forum/(?P<pk>\d+)/$', ForumView.as_view(), name='forum'),

    # User
    url('^users/(?P<username>[^/]+)/$', UserView.as_view(), name='user'),
    url('^block_user/([^/]+)/$', block_user, name='block_user'),
    url('^unblock_user/([^/]+)/$', unblock_user, name='unblock_user'),
    url(r'^users/(?P<username>[^/]+)/topics/$', UserTopics.as_view(), name='user_topics'),
    url(r'^users/(?P<username>[^/]+)/posts/$', UserPosts.as_view(), name='user_posts'),

    # Profile
    url('^profile/edit/$', ProfileEditView.as_view(), name='edit_profile'),

    # Topic
    url('^topics/$', ListCreateTopicsView.as_view(), name='topic_list'),
    url('^topics/(?P<pk>\d+)/$', TopicView.as_view(), name='topic'),
    url('^topics/(?P<pk>\d+)/edit/$', UpdateTopicView.as_view(), name='edit_topic'),
    url('^topics/(?P<pk>\d+)/stick/$', StickTopicView.as_view(), name='stick_topic'),
    url('^topics/(?P<pk>\d+)/unstick/$', UnstickTopicView.as_view(), name='unstick_topic'),
    url('^topics/(?P<pk>\d+)/close/$', CloseTopicView.as_view(), name='close_topic'),
    url('^topics/(?P<pk>\d+)/open/$', OpenTopicView.as_view(), name='open_topic'),
    url('^topics/(?P<pk>\d+)/poll_vote/$', TopicPollVoteView.as_view(), name='topic_poll_vote'),
    url('^topics/(?P<pk>\d+)/cancel_poll_vote/$', topic_cancel_poll_vote, name='topic_cancel_poll_vote'),

    # Subscription
    url('^topics/(?P<pk>\d+)/unsubscribe/$', delete_subscription, name='delete_subscription'),
    url('^topics/(?P<pk>\d+)/subscribe/$', add_subscription, name='add_subscription'),

    # Post
    url('^posts/$', CreatePostView.as_view(), name='add_post'),
    url('^posts/(?P<pk>\d+)/$', PostView.as_view(), name='post'),
    url('^posts/(?P<pk>\d+)/edit/$', UpdatePostView.as_view(), name='edit_post'),
    url('^posts/(?P<pk>\d+)/delete/$', DeletePostView.as_view(), name='delete_post'),
    url('^posts/(?P<pk>\d+)/moderate/$', moderate_post, name='moderate_post'),

    # Preview markup as html
    url('^preview/', preview_post, name='preview_post'),

    # Commands
    url('^mark_all_as_read/$', mark_all_as_read, name='mark_all_as_read'),

    # Human readable urls
    url(r'^c/(?P<slug>[\w-]+)/$', CategoryView.as_view(), name='category'),
    url(r'^c/(?P<category_slug>[\w-]+)/(?P<slug>[\w-]+)/$', ForumView.as_view(), name='forum'),
    url(r'^c/(?P<category_slug>[\w-]+)/(?P<forum_slug>[\w-]+)/(?P<slug>[\w-]+)/$', TopicView.as_view(), name='topic'),
]
