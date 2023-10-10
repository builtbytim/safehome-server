import logging
from .config.settings import get_settings

settings = get_settings()


class Logger:
    "Log service"

    def __init__(self, fn) -> None:

        self.logger = logging.getLogger(fn)

        # Handlers
        stream_handler = logging.StreamHandler()
        # file_handler = logging.FileHandler(f'./logs/{fn}.log', "a")

        # Default Log Levels
        if settings.debug:
            stream_handler.setLevel(logging.DEBUG)
            # file_handler.setLevel(logging.DEBUG)

        else:
            stream_handler.setLevel(logging.INFO)
            # file_handler.setLevel(logging.WARNING)

        # formatters
        stream_formatter = logging.Formatter(
            '%(name)s - %(levelname)s - %(message)s')
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        # hook up
        stream_handler.setFormatter(stream_formatter)
        # file_handler.setFormatter(file_formatter)

        self.logger.addHandler(stream_handler)
        # self.logger.addHandler(file_handler)

    def debug(self, msg, *args, **kwargs):

        self.logger.log(logging.DEBUG, msg, *args, **kwargs)

    def info(self, msg, *args, **kwargs):

        self.logger.log(logging.INFO, msg, *args, **kwargs)

    def warn(self, msg, *args, **kwargs):

        self.logger.log(logging.WARNING, msg, *args, **kwargs)

    def error(self, msg, *args, **kwargs):

        self.logger.log(logging.ERROR, msg, *args, **kwargs)

    def fatal(self, msg, *args, **kwargs):

        self.logger.log(logging.CRITICAL, msg, *args, **kwargs)

    def critical(self, msg, *args, **kwargs):

        self.logger.log(logging.CRITICAL, msg, *args, **kwargs)
