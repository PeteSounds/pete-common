"""BASE_PATH-aware url helpers for apps hosted under a Caddy subpath.

Set the base path once at app startup:

    import pete_common.urls as urls
    urls.BASE_PATH = config.get("base_path", "")

then use urls.url() / urls.url_for() exactly like the old per-app urls.py.
Flask is imported lazily inside url_for so this module loads without it.
"""

BASE_PATH = ""


def url(path):
    if not path or path.startswith(("http://", "https://", "//")):
        return path
    if not path.startswith("/"):
        path = "/" + path
    if BASE_PATH and not path.startswith(BASE_PATH + "/"):
        return BASE_PATH + path
    return path


def url_for(endpoint, **values):
    from flask import url_for as _url_for
    return url(_url_for(endpoint, **values))
