##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import json
from django.db.models import Q
from datetime import timedelta
from django.utils import timezone
from django.form import ValidationException
from account.models import Lab

from resource_inventory.models import (
    ResourceTemplate,
    Installer,
    Image,
    OPNFVRole,
    OPNFVConfig,
    HostOPNFVConfig,
)
from resource_inventory.resource_manager import ResourceManager
from resource_inventory.pdf_templater import PDFTemplater
from notifier.manager import NotificationHandler
from booking.models import Booking
from dashboard.exceptions import BookingLengthException
from api.models import JobFactory


def parse_resource_field(resource_json):
    """
    Parse the json from the frontend.

    returns a reference to the selected Lab and ResourceTemplate objects
    """
    lab, template = (None, None)
    lab_dict = resource_json['lab']
    for lab_info in lab_dict.values():
        if lab_info['selected']:
            lab = Lab.objects.get(lab_user__id=lab_info['id'])

    resource_dict = resource_json['resource']
    for resource_info in resource_dict.values():
        if resource_info['selected']:
            template = ResourceTemplate.objects.get(pk=resource_info['id'])

    if lab is None:
        raise ValidationException("No lab was selected")
    if template is None:
        raise ValidationException("No Host was selected")

    return lab, template


def update_template(template, image, lab, hostname):
    """
    Update and copy a resource template to the user's profile.

    TODO: How, why, should we?
    """
    pass


def generate_opnfvconfig(scenario, installer, template):
    return OPNFVConfig.objects.create(
        scenario=scenario,
        installer=installer,
        template=template
    )


def generate_hostopnfv(hostconfig, opnfvconfig):
    role = None
    try:
        role = OPNFVRole.objects.get(name="Jumphost")
    except Exception:
        role = OPNFVRole.objects.create(
            name="Jumphost",
            description="Single server jumphost role"
        )
    return HostOPNFVConfig.objects.create(
        role=role,
        host_config=hostconfig,
        opnfv_config=opnfvconfig
    )


def generate_resource_bundle(template):
    resource_manager = ResourceManager.getInstance()
    resource_bundle = resource_manager.convertResourceBundle(template)
    return resource_bundle


def check_invariants(request, **kwargs):
    # TODO: This should really happen in the BookingForm validation methods
    installer = kwargs['installer']
    image = kwargs['image']
    scenario = kwargs['scenario']
    lab = kwargs['lab']
    host_profile = kwargs['host_profile']
    length = kwargs['length']
    # check that image os is compatible with installer
    if installer in image.os.sup_installers.all():
        # if installer not here, we can omit that and not check for scenario
        if not scenario:
            raise ValidationException("An OPNFV Installer needs a scenario to be chosen to work properly")
        if scenario not in installer.sup_scenarios.all():
            raise ValidationException("The chosen installer does not support the chosen scenario")
    if image.from_lab != lab:
        raise ValidationException("The chosen image is not available at the chosen hosting lab")
    if image.host_type != host_profile:
        raise ValidationException("The chosen image is not available for the chosen host type")
    if not image.public and image.owner != request.user:
        raise ValidationException("You are not the owner of the chosen private image")
    if length < 1 or length > 21:
        raise BookingLengthException("Booking must be between 1 and 21 days long")


def create_from_form(form, request):
    """
    Create a Booking from the user's form.

    Large, nasty method to create a booking or return a useful error
    based on the form from the frontend
    """
    resource_field = form.cleaned_data['filter_field']
    purpose_field = form.cleaned_data['purpose']
    project_field = form.cleaned_data['project']
    users_field = form.cleaned_data['users']
    hostname = form.cleaned_data['hostname']
    length = form.cleaned_data['length']

    image = form.cleaned_data['image']
    scenario = form.cleaned_data['scenario']
    installer = form.cleaned_data['installer']

    lab, resource_template = parse_resource_field(resource_field)
    data = form.cleaned_data
    data['lab'] = lab
    data['resource_template'] = resource_template
    check_invariants(request, **data)

    # check booking privileges
    # TODO: use the canonical booking_allowed method because now template might have multiple
    # machines
    if Booking.objects.filter(owner=request.user, end__gt=timezone.now()).count() >= 3 and not request.user.userprofile.booking_privledge:
        raise PermissionError("You do not have permission to have more than 3 bookings at a time.")

    ResourceManager.getInstance().templateIsReservable(resource_template)

    hconf = update_template(resource_template, image, lab, hostname)

    # if no installer provided, just create blank host
    opnfv_config = None
    if installer:
        opnfv_config = generate_opnfvconfig(scenario, installer, resource_template)
        generate_hostopnfv(hconf, opnfv_config)

    # generate resource bundle
    resource_bundle = generate_resource_bundle(resource_template)

    # generate booking
    booking = Booking.objects.create(
        purpose=purpose_field,
        project=project_field,
        lab=lab,
        owner=request.user,
        start=timezone.now(),
        end=timezone.now() + timedelta(days=int(length)),
        resource=resource_bundle,
        opnfv_config=opnfv_config
    )
    booking.pdf = PDFTemplater.makePDF(booking)

    for collaborator in users_field:  # list of UserProfiles
        booking.collaborators.add(collaborator.user)

    booking.save()

    # generate job
    JobFactory.makeCompleteJob(booking)
    NotificationHandler.notify_new_booking(booking)

    return booking


def drop_filter(user):
    """
    Return a dictionary that contains filters.

    Only certain installlers are supported on certain images, etc
    so the image filter indexed at [imageid][installerid] is truthy if
    that installer is supported on that image
    """
    installer_filter = {}
    for image in Image.objects.all():
        installer_filter[image.id] = {}
        for installer in image.os.sup_installers.all():
            installer_filter[image.id][installer.id] = 1

    scenario_filter = {}
    for installer in Installer.objects.all():
        scenario_filter[installer.id] = {}
        for scenario in installer.sup_scenarios.all():
            scenario_filter[installer.id][scenario.id] = 1

    images = Image.objects.filter(Q(public=True) | Q(owner=user))
    image_filter = {}
    for image in images:
        image_filter[image.id] = {
            'lab': 'lab_' + str(image.from_lab.lab_user.id),
            'host_profile': 'host_' + str(image.host_type.id),
            'name': image.name
        }

    return {'installer_filter': json.dumps(installer_filter),
            'scenario_filter': json.dumps(scenario_filter),
            'image_filter': json.dumps(image_filter)}
