from django.apps import AppConfig
from django.utils.translation import ugettext_lazy as _

default_app_config = 'pybb.PybbConfig'


class PybbConfig(AppConfig):
    name = 'pybb'
    verbose_name = _('Pybbm forum solution')

    def ready(self):
        from pybb import signals
        signals.setup()
