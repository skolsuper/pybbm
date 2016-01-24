from django.core.urlresolvers import reverse

from pybb.models import Post


def test_filters(user, topic, api_client):
    add_post_url = reverse('pybb:add_post')
    api_client.force_authenticate(user)
    values = {
        'topic': topic.id,
        'body': 'test\n \n \n\nmultiple empty lines\n'
    }
    response = api_client.post(add_post_url, values, follow=True)
    assert response.status_code == 201
    assert Post.objects.all()[0].body == 'test\nmultiple empty lines'
