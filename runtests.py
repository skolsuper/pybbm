import os
import sys
from optparse import OptionParser

import django
from django.conf import settings
from django.test.utils import get_runner

project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'test/test_project')
sys.path.insert(0, project_dir)

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'test_project.settings')


def runtests(*test_args, **kwargs):
    if not test_args:
        test_args = ['pybb']

    django.setup()
    Runner = get_runner(settings)
    test_runner = Runner(verbosity=kwargs.get('verbosity', 1), interactive=kwargs.get('interactive', False),
                         failfast=kwargs.get('failfast'))
    failures = test_runner.run_tests(test_args)
    sys.exit(failures)


if __name__ == '__main__':
    parser = OptionParser()
    parser.add_option('--failfast', action='store_true', default=False, dest='failfast')

    (options, args) = parser.parse_args()

    runtests(failfast=options.failfast, *args)
