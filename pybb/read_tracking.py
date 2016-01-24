from django.db.models import Max, F

from pybb.models import ForumReadTracker, TopicReadTracker


def mark_read(user, topic, last_read_time):
    try:
        forum_mark = ForumReadTracker.objects.get(forum=topic.forum, user=user)
    except ForumReadTracker.DoesNotExist:
        forum_mark = None
    if (forum_mark is None) or (forum_mark.time_stamp < last_read_time):
        topic_mark, new = TopicReadTracker.objects.get_or_create(topic=topic, user=user)
        if not new and topic_mark.time_stamp > last_read_time:
            # Bail early if we already read this thread.
            return

        # Check, if there are any unread topics in forum
        readed_trackers = TopicReadTracker.objects\
            .annotate(last_update=Max('topic__posts__created'))\
            .filter(user=user, topic__forum=topic.forum, time_stamp__gte=F('last_update'))
        unread = topic.forum.topics.exclude(topicreadtracker__in=readed_trackers)
        if forum_mark is not None:
            unread = unread.annotate(
                last_update=Max('posts__created')).filter(last_update__gte=forum_mark.time_stamp)

        if not unread.exists():
            # Clear all topic marks for this forum, mark forum as read
            TopicReadTracker.objects.filter(user=user, topic__forum=topic.forum).delete()
            forum_mark = ForumReadTracker.objects.get_or_create(forum=topic.forum, user=user)
            forum_mark.time_stamp = last_read_time
            forum_mark.save()
        else:
            topic_mark.time_stamp = last_read_time
            topic_mark.save()
