from django.utils.lru_cache import lru_cache
from django.utils.module_loading import import_string

from pybb.markup.base import BaseParser
from pybb.settings import settings


@lru_cache()
def get_markup_engine(name=None):
    """
    Returns the named markup engine instance, or the default one if name is not given.
    This function will replace _get_markup_formatter and _get_markup_quoter in the
    next major release.
    """
    name = name or settings.PYBB_MARKUP
    engines_dict = settings.PYBB_MARKUP_ENGINES_PATHS
    if name not in engines_dict:
        engine = BaseParser()
    else:
        engine = engines_dict[name]
        engine = import_string(engine)()
    return engine
