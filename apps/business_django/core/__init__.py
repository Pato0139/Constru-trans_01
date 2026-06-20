from copy import copy as _copy

import django.template.context as _template_context


def _patched_basecontext_copy(self):
    duplicate = self.__class__.__new__(self.__class__)
    duplicate.__dict__.update(getattr(self, '__dict__', {}))
    duplicate.dicts = self.dicts[:] if hasattr(self, 'dicts') else []
    if hasattr(self, 'render_context'):
        duplicate.render_context = _copy(self.render_context)
    return duplicate

_template_context.BaseContext.__copy__ = _patched_basecontext_copy
