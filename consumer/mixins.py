from abc import ABCMeta, abstractmethod


class DictResultMixin(object):
    __metaclass__ = ABCMeta

    @abstractmethod
    def as_dict(self, **params):
        '''Implement this methods to convert the response from service call to a python dictionary'''


class RetryableMixin(object):

    def __init__(self, retryAttempts=3, canRaise=False):
        self.__can_raise = bool(canRaise)
        self.retry_attempts = int(retryAttempts)

    def get(**params):
        for retry_attempt in range(1, self.retry_attempts):
            try:
                super(RetryableMixin, self).get(**params)
                break
            except Exception as ex:
                logging.error('Attempt {} of {} failed'.format(retry_attempt, self.retry_attempts))
                if self.__can_raise:
                    raise
        return self