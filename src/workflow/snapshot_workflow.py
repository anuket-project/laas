##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from django.utils import timezone
import json

from booking.models import Booking
from resource_inventory.models import Host, Image
from workflow.models import WorkflowStep
from workflow.forms import SnapshotMetaForm, SnapshotHostSelectForm


class Select_Host_Step(WorkflowStep):
    template = "snapshot_workflow/steps/select_host.html"
    title = "Select Host"
    description = "Choose which machine you want to snapshot"
    short_title = "host"

    def get_context(self):
        context = super(Select_Host_Step, self).get_context()
        context['form'] = SnapshotHostSelectForm()
        booking_hosts = {}
        now = timezone.now()
        user = self.repo_get(self.repo.SESSION_USER)
        bookings = Booking.objects.filter(start__lt=now, end__gt=now, owner=user)
        for booking in bookings:
            booking_hosts[booking.id] = {}
            booking_hosts[booking.id]['purpose'] = booking.purpose
            booking_hosts[booking.id]['start'] = booking.start.strftime("%Y-%m-%d")
            booking_hosts[booking.id]['end'] = booking.end.strftime("%Y-%m-%d")
            booking_hosts[booking.id]['hosts'] = []
            for genericHost in booking.resource.template.getHosts():
                booking_hosts[booking.id]['hosts'].append({"name": genericHost.resource.name})

        context['booking_hosts'] = booking_hosts

        chosen_host = self.repo_get(self.repo.SNAPSHOT_MODELS, {}).get("host")
        if chosen_host:
            chosen = {}
            chosen['booking_id'] = self.repo_get(self.repo.SNAPSHOT_BOOKING_ID)
            chosen['hostname'] = chosen_host.template.resource.name
            context['chosen'] = chosen
        return context

    def post_render(self, request):
        host_data = request.POST.get("host")
        if not host_data:
            self.metastep.set_invalid("Please select a host")
            return self.render(request)
        host = json.loads(host_data)
        if 'name' not in host or 'booking' not in host:
            self.metastep.set_invalid("Invalid host selected")
            return self.render(request)
        name = host['name']
        booking_id = host['booking']
        booking = Booking.objects.get(pk=booking_id)
        host = Host.objects.get(bundle=booking.resource, template__resource__name=name)
        models = self.repo_get(self.repo.SNAPSHOT_MODELS, {})
        if "host" not in models:
            models['host'] = host
        if 'snapshot' not in models:
            models['snapshot'] = Image()
        self.repo_put(self.repo.SNAPSHOT_MODELS, models)
        self.repo_put(self.repo.SNAPSHOT_BOOKING_ID, booking_id)

        confirm = self.repo_get(self.repo.CONFIRMATION, {})
        snap_confirm = confirm.get("snapshot", {})
        snap_confirm['host'] = name
        confirm['snapshot'] = snap_confirm
        self.repo_put(self.repo.CONFIRMATION, confirm)
        self.metastep.set_valid("Success")
        return self.render(request)


class Image_Meta_Step(WorkflowStep):
    template = "snapshot_workflow/steps/meta.html"
    title = "Additional Information"
    description = "We need some more info"
    short_title = "info"

    def get_context(self):
        context = super(Image_Meta_Step, self).get_context()
        name = self.repo_get(self.repo.SNAPSHOT_NAME, False)
        desc = self.repo_get(self.repo.SNAPSHOT_DESC, False)
        form = None
        if name and desc:
            form = SnapshotMetaForm(initial={"name": name, "description": desc})
        else:
            form = SnapshotMetaForm()
        context['form'] = form
        return context

    def post_render(self, request):
        form = SnapshotMetaForm(request.POST)
        if form.is_valid():
            name = form.cleaned_data['name']
            self.repo_put(self.repo.SNAPSHOT_NAME, name)
            description = form.cleaned_data['description']
            self.repo_put(self.repo.SNAPSHOT_DESC, description)

            confirm = self.repo_get(self.repo.CONFIRMATION, {})
            snap_confirm = confirm.get("snapshot", {})
            snap_confirm['name'] = name
            snap_confirm['description'] = description
            confirm['snapshot'] = snap_confirm
            self.repo_put(self.repo.CONFIRMATION, confirm)

            self.metastep.set_valid("Success")
        else:
            self.metastep.set_invalid("Please Fill out the Form")

        return self.render(request)
