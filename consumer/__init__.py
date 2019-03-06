
from .mixins import RetryableMixin
from .base import *


class RetryableAbstractBaseJsonWebService(AbstractBaseJsonWebService, RetryableMixin):

    def __init__(self, env=None, timeout=None, canRaise=False, retryAttempts=3):
        RetryableAbstractBaseJsonWebService.__init__(self, env=env, canRaise=True)
        RetryableMixin.__init__(self, retryAttempts=retryAttempts, canRaise=canRaise)
