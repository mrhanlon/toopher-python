import urllib
import json
import oauth2
import os
import sys
DEFAULT_BASE_URL = "https://api.toopher.com/v1"
VERSION = "1.0.6"

class ToopherApiError(Exception): pass
class UserDisabledError(ToopherApiError): pass
class UnknownUserError(ToopherApiError): pass
class UnknownTerminalError(ToopherApiError): pass
class PairingDeactivatedError(ToopherApiError): pass
error_codes_to_errors = {704: UserDisabledError,
                         705: UnknownUserError,
                         706: UnknownTerminalError}

class ToopherApi(object):
    def __init__(self, key, secret, api_url=None):
        self.client = oauth2.Client(oauth2.Consumer(key, secret))
        self.client.ca_certs = os.path.join(os.path.dirname(os.path.abspath(__file__)), "toopher.pem")
        base_url = api_url if api_url else DEFAULT_BASE_URL
        self.base_url = base_url.rstrip('/')

    def pair(self, pairing_phrase, user_name, **kwargs):
        uri = self.base_url + "/pairings/create"
        params = {'pairing_phrase': pairing_phrase,
                  'user_name': user_name}

        params.update(kwargs)

        result = self._request(uri, "POST", params)
        return PairingStatus(result)

    def pair_sms(self, phone_number, user_name, phone_country=None):
        uri = self.base_url + "/pairings/create/sms"
        params = {'phone_number': phone_number,
                  'user_name': user_name}

        if phone_country:
            params['phone_country'] = phone_country

        result = self._request(uri, "POST", params)
        return PairingStatus(result)

    def get_pairing_status(self, pairing_id):
        uri = self.base_url + "/pairings/" + pairing_id

        result = self._request(uri, "GET")
        return PairingStatus(result)

    def authenticate(self, pairing_id, terminal_name, action_name=None, **kwargs):
        uri = self.base_url + "/authentication_requests/initiate"
        params = {'pairing_id': pairing_id,
                  'terminal_name': terminal_name}
        if action_name:
            params['action_name'] = action_name

        params.update(kwargs)

        result = self._request(uri, "POST", params)
        return AuthenticationStatus(result)

    def get_authentication_status(self, authentication_request_id):
        uri = self.base_url + "/authentication_requests/" + authentication_request_id

        result = self._request(uri, "GET")
        return AuthenticationStatus(result)

    def authenticate_with_otp(self, authentication_request_id, otp):
        uri = self.base_url + "/authentication_requests/" + authentication_request_id + '/otp_auth'
        params = {'otp' : otp}
        result = self._request(uri, "POST", params)
        return AuthenticationStatus(result)

    def authenticate_by_user_name(self, user_name, terminal_name_extra, action_name, **kwargs):
        kwargs.update(user_name=user_name, terminal_name_extra=terminal_name_extra)
        return self.authenticate('', '', action_name, **kwargs)

    def assign_friendly_name_to_terminal(self, user_name, terminal_name, terminal_name_extra):
        uri = self.base_url + '/user_terminals/create'
        params = {'user_name': user_name,
                  'name': terminal_name,
                  'name_extra': terminal_name_extra}
        result = self._request(uri, 'POST', params)
        return

    def _request(self, uri, method, params=None):
        data = urllib.urlencode(params or {})
        header_data = {'User-Agent':'Toopher-Python/{} (Python {})'.format(VERSION, sys.version.split()[0])}

        response, content = self.client.request(uri, method, data, headers=header_data)
        try:
            content = json.loads(content)
        except ValueError:
            raise ToopherApiError('Response from server could not be decoded as JSON.')

        if int(response['status']) > 300:
            self._parse_request_error(content)

        return content

    def _parse_request_error(self, content):
        error_code = content['error_code']
        error_message = content['error_message']
        if error_code in error_codes_to_errors:
            error = error_codes_to_errors[error_code]
            raise error(error_message)

        # TODO: Add an error code for PairingDeactivatedError.
        if ('pairing has been deactivated' in error_message
            or 'pairing has not been authorized' in error_message):
            raise PairingDeactivatedError(error_message)

        raise ToopherApiError(error_message)

class PairingStatus(object):
    def __init__(self, json_response):
        try:
            self.id = json_response['id']
            self.enabled = json_response['enabled']

            user = json_response['user']
            self.user_id = user['id']
            self.user_name = user['name']
        except Exception as e:
            raise ToopherApiError("Could not parse pairing status from response" + e.message)

        self._raw_data = json_response

    def __nonzero__(self):
        return self.enabled

    def __getattr__(self, name):
        return self._raw_data[name]


class AuthenticationStatus(object):
    def __init__(self, json_response):
        try:
            self.id = json_response['id']
            self.pending = json_response['pending']
            self.granted = json_response['granted']
            self.automated = json_response['automated']
            self.reason = json_response['reason']

            terminal = json_response['terminal']
            self.terminal_id = terminal['id']
            self.terminal_name = terminal['name']
        except Exception:
            raise ToopherApiError("Could not parse authentication status from response")

        self._raw_data = json_response

    def __nonzero__(self):
        return self.granted

    def __getattr__(self, name):
        return self._raw_data[name]
