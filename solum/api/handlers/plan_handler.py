# Copyright (c) 2014 Rackspace Hosting
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

import uuid

from solum.api.handlers import handler
from solum import objects


class PlanHandler(handler.Handler):
    """Fulfills a request on the plan resource."""

    def get(self, id):
        """Return a plan."""
        return objects.registry.Plan.get_by_uuid(self.context, id)

    def _update_raw_content(self, db_obj, data):
        filtered_data = {}
        for dk, dv in iter(data.items()):
            if not hasattr(db_obj, dk) and dk not in ('type', 'uri'):
                filtered_data[dk] = dv
        db_obj.raw_content = filtered_data

    def update(self, id, data):
        """Modify a resource."""
        db_obj = objects.registry.Plan.get_by_uuid(self.context, id)
        db_obj.update(data)
        self._update_raw_content(db_obj, data)
        db_obj.save(self.context)
        return db_obj

    def delete(self, id):
        """Delete a resource."""
        db_obj = objects.registry.Plan.get_by_uuid(self.context, id)
        db_obj.destroy(self.context)

    def create(self, data):
        """Create a new resource."""
        db_obj = objects.registry.Plan()
        db_obj.update(data)
        self._update_raw_content(db_obj, data)
        db_obj.uuid = str(uuid.uuid4())
        db_obj.user_id = self.context.user
        db_obj.project_id = self.context.tenant
        db_obj.create(self.context)
        return db_obj

    def get_all(self):
        """Return all plans."""
        return objects.registry.PlanList.get_all(self.context)
