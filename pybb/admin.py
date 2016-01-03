# -*- coding: utf-8
from __future__ import unicode_literals

from django.contrib import admin
from django.contrib.auth import get_user_model
from django.utils.translation import ugettext_lazy as _

from pybb import util
from pybb.models import Category, Forum, Topic, Post, Profile, PollAnswer

username_field = get_user_model().USERNAME_FIELD


class ForumInlineAdmin(admin.TabularInline):
    model = Forum
    fields = ['name', 'hidden', 'position']
    extra = 0


class CategoryAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'position', 'hidden', 'forum_count']
    list_per_page = 20
    ordering = ['position']
    search_fields = ['name']
    list_editable = ['position']

    inlines = [ForumInlineAdmin]

    def forum_count(self, category):
        return category.forums.count()


class ForumAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'category', 'hidden', 'position', 'topic_count', ]
    list_per_page = 20
    raw_id_fields = ['moderators']
    ordering = ['-category']
    search_fields = ['name', 'category__name']
    list_editable = ['position', 'hidden']
    fieldsets = (
        (None, {
                'fields': ('category', 'parent', 'name', 'hidden', 'position', )
                }
         ),
        (_('Additional options'), {
                'classes': ('collapse',),
                'fields': ('updated', 'description', 'headline', 'post_count', 'moderators', 'slug')
                }
            ),
        )

    def topic_count(self, forum):
        return forum.topics.count()


class PollAnswerAdmin(admin.TabularInline):
    model = PollAnswer
    fields = ['text', ]
    extra = 0


class TopicAdmin(admin.ModelAdmin):
    prepopulated_fields = {'slug': ('name',)}
    list_display = ['name', 'forum', 'created', 'head', 'post_count', 'poll_type',]
    list_per_page = 20
    raw_id_fields = ['user', 'subscribers']
    ordering = ['-created']
    date_hierarchy = 'created'
    search_fields = ['name']
    fieldsets = (
        (None, {
                'fields': ('forum', 'name', 'user', ('created', 'updated'), 'poll_type',)
                }
         ),
        (_('Additional options'), {
                'classes': ('collapse',),
                'fields': (('views', 'post_count'), ('sticky', 'closed'), 'subscribers', 'slug')
                }
         ),
        )
    inlines = [PollAnswerAdmin, ]

    def post_count(self, topic):
        return topic.posts.count()

class TopicReadTrackerAdmin(admin.ModelAdmin):
    list_display = ['topic', 'user', 'time_stamp']
    search_fields = ['user__%s' % username_field]

class ForumReadTrackerAdmin(admin.ModelAdmin):
    list_display = ['forum', 'user', 'time_stamp']
    search_fields = ['user__%s' % username_field]

class PostAdmin(admin.ModelAdmin):
    list_display = ['topic', 'user', 'created', 'updated', 'summary']
    list_per_page = 20
    raw_id_fields = ['user', 'topic']
    ordering = ['-created']
    date_hierarchy = 'created'
    search_fields = ['body']
    fieldsets = (
        (None, {
                'fields': ('topic', 'user')
                }
         ),
        (_('Additional options'), {
                'classes': ('collapse',),
                'fields' : (('created', 'updated'), 'user_ip')
                }
         ),
        (_('Message'), {
                'fields': ('body',)
                }
         ),
        )


class ProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'time_zone', 'language', 'post_count']
    list_per_page = 20
    ordering = ['-user']
    search_fields = ['user__%s' % username_field]
    fieldsets = (
        (None, {
                'fields': ('time_zone', 'language')
                }
         ),
        (_('Additional options'), {
                'classes': ('collapse',),
                'fields' : ('avatar', 'signature', 'show_signatures')
                }
         ),
        )

    def post_count(self, profile):
        return profile.user.posts.count()


admin.site.register(Category, CategoryAdmin)
admin.site.register(Forum, ForumAdmin)
admin.site.register(Topic, TopicAdmin)
admin.site.register(Post, PostAdmin)

if util.get_pybb_profile_model() == Profile:
    admin.site.register(Profile, ProfileAdmin)

# This can be used to debug read/unread trackers

#admin.site.register(TopicReadTracker, TopicReadTrackerAdmin)
#admin.site.register(ForumReadTracker, ForumReadTrackerAdmin)
