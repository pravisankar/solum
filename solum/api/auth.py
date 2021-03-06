# -*- encoding: utf-8 -*-
#
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import re

from keystoneclient.middleware import auth_token
from oslo.config import cfg
from pecan import hooks

from solum.common import context
from solum.openstack.common.gettextutils import _
from solum.openstack.common import log as logging


LOG = logging.getLogger(__name__)

OPT_GROUP_NAME = 'keystone_authtoken'

AUTH_OPTS = [
    cfg.BoolOpt('enable_authentication',
                default=True,
                help='This option enables or disables user authentication '
                'via keystone. Default value is True.'),
]

CONF = cfg.CONF
CONF.register_opts(AUTH_OPTS)
CONF.register_opts(auth_token.opts, group=OPT_GROUP_NAME)


def install(app, conf):
    if conf.get('enable_authentication'):
        return AuthProtocolWrapper(app, conf=dict(conf.get(OPT_GROUP_NAME)))
    else:
        LOG.warning(_('Keystone authentication is disabled by Solum '
                      'configuration parameter enable_authentication. '
                      'Solum will not authenticate incoming request. '
                      'In order to enable authentication set '
                      'enable_authentication option to True.'))

    return app


class AuthProtocolWrapper(auth_token.AuthProtocol):
    """A wrapper on Keystone auth_token AuthProtocol.

    Does not perform verification of authentication tokens for pub routes in
    the API. Public routes are those which Uri starts with
    '/{version_number}/public/'

    """

    def __call__(self, env, start_response):
        path = env.get('PATH_INFO')
        regexp = re.compile('^/v[0-9]+/public/')
        if regexp.match(path):
            return self.app(env, start_response)
        return super(AuthProtocolWrapper, self).__call__(env, start_response)


class AuthInformationHook(hooks.PecanHook):

    def before(self, state):
        if not CONF.get('enable_authentication'):
            return
        #Do not proceed for triggers as they use non authenticated service
        regexp = re.compile('^/v[0-9]+/public/')
        if regexp.match(state.request.path):
            return

        headers = state.request.headers
        user_id = headers.get('X-User-Id')
        if user_id is None:
            LOG.debug("X-User-Id header was not found in the request")
            raise Exception('Not authorized')

        roles = self._get_roles(state.request)

        project_id = headers.get('X-Project-Id')
        user_name = headers.get('X-User-Name', '')

        domain = headers.get('X-Domain-Name')
        project_domain_id = headers.get('X-Project-Domain-Id', '')
        user_domain_id = headers.get('X-User-Domain-Id', '')

        # Get the auth token
        try:
            recv_auth_token = headers.get('X-Auth-Token',
                                          headers.get(
                                              'X-Storage-Token'))
        except ValueError:
            LOG.debug("No auth token found in the request.")
            raise Exception('Not authorized')

        service_catalog = None
        if headers.get('X-Service-Catalog') is not None:
            try:
                # We will not parse service catalog here
                # service_catalog will contain json formatted string
                service_catalog = headers.get('X-Service-Catalog')
            except ValueError:
                raise Exception(
                    _('Invalid service catalog json.'))
        identity_status = headers.get('X-Identity-Status')
        if identity_status == 'Confirmed':
            ctx = context.RequestContext(auth_token=recv_auth_token,
                                         user=user_id,
                                         tenant=project_id,
                                         domain=domain,
                                         user_domain=user_domain_id,
                                         project_domain=project_domain_id,
                                         user_name=user_name,
                                         roles=roles,
                                         service_catalog=service_catalog)
            state.request.security_context = ctx
        else:
            LOG.debug("The provided identity is not confirmed.")
            raise Exception('Not authorized. Identity not confirmed.')
        return

    def _get_roles(self, req):
        """Get the list of roles."""

        if 'X-Roles' in req.headers:
            roles = req.headers.get('X-Roles', '')
        else:
            # Fallback to deprecated role header:
            roles = req.headers.get('X-Role', '')
            if roles:
                LOG.warn(_("X-Roles is missing. Using deprecated X-Role "
                           "header"))
        return [r.strip() for r in roles.split(',')]
