"""app.proxy: translate request from AWS api-gateway
Freely adapted from https://github.com/aws/chalice
"""

import re
import sys
import json
import logging

_PARAMS = re.compile('<\w+\:?\w+>')


class Request(object):
    '''The current request from API gateway.'''

    def __init__(self, query_params, uri_params, method):
        self.query_params = query_params
        self.uri_params = uri_params
        self.method = method


class RouteEntry(object):

    def __init__(self, view_function, view_name, path, methods, cors=False):
        self.view_function = view_function
        self.view_name = view_name
        self.uri_pattern = path
        self.methods = methods
        self.view_args = self._parse_view_args()
        self.cors = cors

    def _parse_view_args(self):
        if '{' not in self.uri_pattern:
            return []
        # The [1:-1] slice is to remove the braces
        # e.g {foobar} -> foobar
        results = [r[1:-1] for r in _PARAMS.findall(self.uri_pattern)]
        return results

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class API(object):

    FORMAT_STRING = '[%(name)s] - [%(levelname)s] - %(message)s'

    def __init__(self, app_name, configure_logs=True):
        self.app_name = app_name
        self.routes = {}
        self.current_request = None
        self.debug = True
        self.configure_logs = configure_logs
        self.log = logging.getLogger(self.app_name)
        if self.configure_logs:
            self._configure_logging()

    def _configure_logging(self):
        log = logging.getLogger(self.app_name)
        if self._already_configured(log):
            return
        handler = logging.StreamHandler(sys.stdout)
        # Timestamp is handled by lambda itself so the
        # default FORMAT_STRING doesn't need to include it.
        formatter = logging.Formatter(self.FORMAT_STRING)
        handler.setFormatter(formatter)
        log.propagate = False
        if self.debug:
            level = logging.DEBUG
        else:
            level = logging.ERROR
        log.setLevel(level)
        log.addHandler(handler)

    def _already_configured(self, log):
        if not log.handlers:
            return False
        for handler in log.handlers:
            if isinstance(handler, logging.StreamHandler):
                if handler.stream == sys.stdout:
                    return True
        return False

    def route(self, path, **kwargs):
        def _register_view(view_func):
            self._add_route(path, view_func, **kwargs)
            return view_func
        return _register_view

    def _add_route(self, path, view_func, **kwargs):
        name = kwargs.pop('name', view_func.__name__)
        methods = kwargs.pop('methods', ['GET'])
        cors = kwargs.pop('cors', False)

        if kwargs:
            raise TypeError('TypeError: route() got unexpected keyword '
                            'arguments: {}'.format(', '.join(list(kwargs))))

        if path in self.routes:
            raise ValueError(
                'Duplicate route detected: "{}"\n'
                'URL paths must be unique.'.format(path))

        entry = RouteEntry(view_func, name, path, methods, cors)
        self.routes[path] = entry

    def _url_matching(self, url):
        for path, function in self.routes.items():
            path = re.sub('<\w+>', '\w+', path)
            path = re.sub('<int\:\w+>', '\d+', path)
            path = re.sub('<float\:\w+>', '[+-]?([0-9]*[.])?[0-9]+', path)
            path = re.sub('<string\:\w+>', '\w+', path)
            path = re.sub('<uuid\:\w+>', '[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}', path)
            route_expr = re.compile(path)

            if route_expr.match(url):
                return True

        return False

    def _get_route_match(self, url):
        for path, function in self.routes.items():
            route_expr = re.compile(re.sub('<\w+\:?\w+>', '\w+', path))
            if route_expr.match(url):
                return path
        return ''

    def _converters(self, value, pathArg):
        conv_expr = re.compile('<\w+\:\w+>')
        if conv_expr.match(pathArg):
            if pathArg.split(':')[0] == '<int':
                value = re.sub('[^\d]', '', value)
                return int(eval(value))
            elif pathArg.split(':')[0] == '<float':
                return float(eval(value))
            elif pathArg.split(':')[0] == '<string':
                return value
            elif pathArg.split(':')[0] == '<uuid':
                return value
            else:
                return value
        else:
            return value

    def _get_matching_args(self, route, url):
        url_expr = re.compile('\w+')
        route_expr = re.compile('\w+|<\w+\:?\w+>')

        url_args = url_expr.findall(url)
        route_args = route_expr.findall(route)

        args = [
            self._converters(url_args[u], route_args[u])
            for u in range(len(url_args))
            if url_args[u] != route_args[u]]

        return args

    def response(self, status, content_type, response_body, cors=False):
        '''
        Return HTTP response, including
        response code (status), headers and body
        '''

        statusCode = {
            'OK': '200',
            'EMPTY': '204',
            'NOK': '400',
            'FOUND': '302',
            'NOT_FOUND': '404',
            'CONFLICT': '409',
            'ERROR': '500'}

        messageData = {
            'statusCode': statusCode[status],
            'body': response_body,
            'headers': {'Content-Type': content_type}}

        if cors:
            messageData['headers']['Access-Control-Allow-Origin'] = '*'
            messageData['headers']['Access-Control-Allow-Methods'] = 'GET'

        if content_type in ['image/png', 'image/jpeg']:
            messageData['isBase64Encoded'] = True

        return messageData

    def __call__(self, event, context):

        resource_path = event['path']
        if resource_path is None:
            return self.response('NOK', 'application/json', json.dumps({
                'errorMessage': 'Bad Route: {resource_path}'}))

        if not self._url_matching(resource_path):
            return self.response('NOK', 'application/json', json.dumps({
                'errorMessage': 'No view function for: {}'.format(resource_path)}))

        route_entry = self.routes[self._get_route_match(resource_path)]

        http_method = event['httpMethod']
        if http_method not in route_entry.methods:
            return self.response('NOK', 'application/json', json.dumps({
                'errorMessage': 'Unsupported method: {}'.format(http_method)}), route_entry.cors)

        view_function = route_entry.view_function

        function_args = self._get_matching_args(route_entry.uri_pattern, resource_path)

        self.current_request = Request(event['queryStringParameters'],
                                       event['path'],
                                       event['httpMethod'])

        try:
            response = view_function(*function_args)

        except Exception as err:
            self.log.error(str(err))
            response = ('ERROR', 'application/json', json.dumps({'errorMessage': str(err)}))

        return self.response(response[0], response[1], response[2], route_entry.cors)
