from django.db.models import Q

from pybb import permissions


class CustomPermissionHandler(permissions.DefaultPermissionHandler):
    """
    a custom permission handler which changes the meaning of "hidden" forum:
    "hidden" forum or category is visible for all logged on users, not only staff
    """

    def filter_categories(self, user, qs):
        return qs.filter(hidden=False) if user.is_anonymous() else qs

    def may_view_category(self, user, category):
        return user.is_authenticated() if category.hidden else True

    def filter_forums(self, user, qs):
        if user.is_anonymous():
            qs = qs.filter(Q(hidden=False) & Q(category__hidden=False))
        return qs

    def may_view_forum(self, user, forum):
        return user.is_authenticated() if forum.hidden or forum.category.hidden else True

    def filter_topics(self, user, qs):
        if user.is_anonymous():
            qs = qs.filter(Q(forum__hidden=False) & Q(forum__category__hidden=False))
        qs = qs.filter(closed=False)  # filter out closed topics for test
        return qs

    def may_view_topic(self, user, topic):
        return self.may_view_forum(user, topic.forum)

    def filter_posts(self, user, qs):
        if user.is_anonymous():
            qs = qs.filter(Q(topic__forum__hidden=False) & Q(topic__forum__category__hidden=False))
        return qs

    def may_view_post(self, user, post):
        return self.may_view_forum(user, post.topic.forum)

    def may_create_poll(self, user):
        return False

    def may_edit_topic_slug(self, user):
        return True


class RestrictEditingHandler(permissions.DefaultPermissionHandler):
    def may_create_topic(self, user, forum):
        return False

    def may_create_post(self, user, topic):
        return False

    def may_edit_post(self, user, post):
        return False
