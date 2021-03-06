# Copyright 2014 - Mirantis, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import inspect
import json

from solum.openstack.common import context


class RequestContext(context.RequestContext):
    def __init__(self, auth_token=None, user=None, tenant=None, domain=None,
                 user_domain=None, project_domain=None, is_admin=False,
                 read_only=False, request_id=None, user_name=None, roles=None,
                 service_catalog=None):
        super(RequestContext, self).__init__(auth_token=auth_token,
                                             user=user, tenant=tenant,
                                             domain=domain,
                                             user_domain=user_domain,
                                             project_domain=project_domain,
                                             is_admin=is_admin,
                                             read_only=read_only,
                                             show_deleted=False,
                                             request_id=request_id)
        self.roles = roles
        self.user_name = user_name
        self._service_catalog_js = None
        self.service_catalog = service_catalog

    def get_url_for(self, service_type=None, endpoint_type=None):
        if self._service_catalog_js is None:
            self._service_catalog_js = json.loads(self.service_catalog)

        for sc in self._service_catalog_js:
            if sc['type'] == service_type:
                for ep in sc['endpoints']:
                    if endpoint_type in ep:
                        return ep[endpoint_type]

    @property
    def auth_url(self):
        return self.get_url_for(service_type='identity',
                                endpoint_type='publicURL')

    def to_dict(self):
        data = super(RequestContext, self).to_dict()
        data.update(roles=self.roles,
                    user_name=self.user_name,
                    service_catalog=self.service_catalog)
        return data

    @classmethod
    def from_dict(cls, values):
        allowed = [arg for arg in
                   inspect.getargspec(RequestContext.__init__).args
                   if arg != 'self']
        kwargs = dict((k, v) for (k, v) in values.items() if k in allowed)
        return cls(**kwargs)
