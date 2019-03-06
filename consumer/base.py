'''
base module 
'''
from abc import ABCMeta, abstractproperty, abstractmethod
from pprint import pformat
from defusedxml import ElementTree
from collections import namedtuple
from mixins import DictResultMixin, RetryableMixin
import requests
import logging
import json

logger = logging.getLogger('app')

ServiceHostCollection = namedtuple('ServiceHostCollection', 'PROD UAT')
ServiceHostCollection.__new__.__defaults__ = (None,)

ServiceHost = namedtuple('ServiceHost', 'host port')
ServiceHost.__new__.__defaults__ = (None,)


class AbstractBaseWebService(object):
    """
        :param env: env name to use.
        
    """
    __metaclass__ = ABCMeta

    content = None

    def __init__(self, env=None, timeout=None, canRaise=False):
        self.is_prod = env and str(env).strip().lower() == 'prod'
        self.timeout = float(timeout) if timeout else None
        self.__can_raise = bool(canRaise)

    @property
    def protocol(self):
        '''http or https'''
        return 'http'

    def headers(self):
        '''optional headers that should be passed with the HTTP request'''
        pass

    def verify(self):
        '''optional verify parameter that should be passed with the HTTP request for verfication'''
        pass

    @abstractproperty
    def hosts(self):
        ''' Concrete Service should define a "hosts" property that should be a ServiceHostCollection with UAT and PROD values'''

    def isAthunticationRequired(self):
        ''' Concrete Service should define a "hosts" property that should be a ServiceHostCollection with UAT and PROD values'''
        return False

    @abstractproperty
    def service_path(self):
        ''' Concrete Service must have a property "service_path" that should be a string representing a absolute path(except the protocol and hostname/port)
            Example:
            for a service http://supercomputer:8080/servicepath/some-end-point
            service_path will be 'servicepath/some-end-point'
        '''

    @property
    def url(self):
        ''' Construct the complete service URI using proper protocol host, port and service_path '''
        if not isinstance(self.hosts, ServiceHostCollection):
            logger.error('hosts property of %s is not a ServiceHostCollection', self.__class__.__name__)
            return None
        servicehost = self.hosts.PROD if self.is_prod else self.hosts.UAT
        if not servicehost:
            if not self.is_prod and self.hosts.PROD:
                logger.info('Falling back to use PROD host since no UAT host specified for %s', self.__class__.__name__)
                servicehost = self.hosts.PROD
            else:
                return None
        host = servicehost.host
        if servicehost.port:
            host = '{}:{}'.format(host, servicehost.port)
        return '{}://{}/{}'.format(self.protocol, host, self.service_path)

    @abstractproperty
    def valid_params(self):
        ''' Service must have a property "valid_params" which is a list of valid query parameter for the service,
            any other parameter passed other than what is defined here will be dropped with a warn log
        '''

    @property
    def mandatory_param_rules(self):
        """Service can optionally define a property "mandatory_params"
        which is a tuple of parameters combination,
        representing set of required query parameter for the service.

        Parameters passed to get method will be checked to have all of
        these params else the web service call will not continue
        default [] empty list no parameters are mandatory

        Returns:
            a tuple of pairs of parameters
            
            >>>``(('param1',), ('param2',),)``
            ``param1`` or ``param2`` should be present
            
            ``(('param1','param2'), ('param3',),)``
            either ``param1`` and ``param2`` paramters should be present or just ``Name`` parameter should be present in the query parameters
        """
        return tuple()

    def _parse_params(self, **kawrs):
        '''parse the parameters passed and drop invalid params also drop invalid values params'''
        params = dict(kawrs)
        for param, value in kawrs.items():
            if param not in self.valid_params:
                logger.warn('dropping "%s" since it is not a valid paramater for %s', param, self.__class__.__name__)
                del params[param]
            if value is None:
                logger.warn('dropping query parameter "%s" for None value', param)
                del params[param]
        return params

    def _has_mandatory_params(self, **params):
        ''' Iterates over the "mandatory_param_rules" property and checkes if parametes match any of the rules specified'''
        set_params = set(params)
        valid = False if len(self.mandatory_param_rules) > 0 else True
        for rule in self.mandatory_param_rules:
            if not set(rule) - set_params:
                valid = True
                break
        return valid

    def get(self, **params):
        '''return a string or None representing response from calling the service URI'''
        self.content = None
        if not self.url:
            logger.error('Cannot use %s No Host specified.', self.__class__.__name__)
            return self
        params = self._parse_params(**params)
        if not self._has_mandatory_params(**params):
            logger.error('Cannot request %s without mandatory params\nParams: %s\nMandatory Rules: %s',
                         self.__class__.__name__, params, self.mandatory_param_rules)
            return self
        logger.info('GET request to %s with params %s', self.url, pformat(params))
        try:
            response = requests.get(self.url,
                                    params=params,
                                    headers=self.headers(),
                                    verify=self.verify(),
                                    timeout=self.timeout)
            if response.ok:
                self.content = response.content
            else:
                logger.warn('Response was not OK Response: "%s"', response.content)
        except Exception as ex:
            logger.warn('Exception occured while consuming %s\n Exception: "%s"', self.__class__.__name__, str(ex))
            if self.__can_raise:
                raise
        return self


class AbstractWebAuth(object):

    @abstractmethod
    def auth_headers(self):
        '''return a dict containing headers that should ne included in a Authenticated HTTP request'''
        return {}

    @abstractmethod
    def certificates(self):
        '''return a string representing the certificate content'''
        return None


class AbstractBaseJsonWebService(AbstractBaseWebService, DictResultMixin):
    '''Use this abstract class when the service is providing JSON reponse and you want the result as a python dictionary '''

    json = None

    def __init__(self, env=None, timeout=None, canRaise=False):
        AbstractBaseJsonWebService.__init__(self, env=env, timeout=timeout, canRaise=True)
        self.__can_raise = bool(canRaise)

    def get(self, **params):
        '''
            deligate the call to super `get` method,
            also try parsing the response as json and store it in self.json
        '''
        self.json = None
        super(AbstractBaseJsonWebService, self).get(**params)
        if self.content:
            try:
                self.json = json.loads(self.content)
            except ValueError as ex:
                logger.error('Response was not in JSON format. Response: "%s" Exception: %s', self.content, str(ex))
                if self.__can_raise:
                    raise
        return self

    def as_dict(self):
        '''return a dictionary or None representing response from calling the service URI'''
        logger.warn('Depricated method: instead of as_dict() just use .json to get a python equivalent object from JSON response')
        if not self.json:
            logger.warn('Response was not in JSON format. hence cannot convert it to a dictonary')
            return None
        return self.json


class AbstractBaseXmlWebService(AbstractBaseWebService, DictResultMixin):
    '''Use this abstract class when the service is providing XML reponse and you want the result as a python dictionary '''

    xml = None

    def __init__(self, env=None, timeout=None, canRaise=False):
        AbstractBaseWebService.__init__(self, env=env, timeout=timeout, canRaise=True)
        self.__can_raise = bool(canRaise)

    def get(self, **params):
        '''
            deligate the call to super `get` method,
            also try parsing the response as XML and store it in self.xml as a defusedxml.ElementTree
        '''
        self.xml = None
        super(AbstractBaseXmlWebService, self).get(**params)
        if self.content:
            try:
                self.xml = ElementTree.fromstring(self.content)
            except ElementTree.ParseError:
                logger.exception('Response was not in proper XML format.')
                self.xml = None
                if self.__can_raise:
                    raise
        return self

    def _xml_to_dict(self, node):
        ''' recursively converts a xml Element to a dictionary '''
        data = {}
        for e in node.getchildren():
            key = e.tag.split('}', 2)[1] if '}' in e.tag else e.tag  # skip namespaces
            value = e.text.strip() if e.text and e.text.strip() else self._xml_to_dict(e)
            data[key] = value
        return data

    def as_dict(self, **params):
        '''return a dictionary or None representing response from calling the service URI'''
        if not self.xml:
            logger.error('Reponse was not a XML, hence cannot convert it to a python dictionary')
            return None
        return self._xml_to_dict(self.xml)
