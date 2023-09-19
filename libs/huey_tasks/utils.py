import functools
from .config import huey


def exp_backoff_task(retries=10, retry_backoff=1.15, retry_delay=1):
    def deco(fn):
        @functools.wraps(fn)
        def inner(*args, **kwargs):

            task = kwargs.pop('task')
            try:
                return fn(*args, **kwargs)
            except Exception as exc:
                task.retry_delay *= retry_backoff
                raise exc

        return huey.task(retries=retries, retry_delay=retry_delay, context=True)(inner)
    return deco
