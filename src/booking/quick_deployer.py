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
from django.core.exceptions import ValidationError
from account.models import Lab

from resource_inventory.models import (
    ResourceTemplate,
    Installer,
    Image,
    OPNFVRole,
    OPNFVConfig,
    ResourceOPNFVConfig,
    ResourceConfiguration,
    NetworkConnection,
    InterfaceConfiguration,
    Network,
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
        raise ValidationError("No lab was selected")
    if template is None:
        raise ValidationError("No Host was selected")

    return lab, template


def update_template(old_template, image, hostname, user):
    """
    Duplicate a template to the users account and update configured fields.

    The dashboard presents users with preconfigured resource templates,
    but the user might want to make small modifications, e.g hostname and
    linux distro. So we copy the public template and create a private version
    to the user's profile, and mark it temporary. When the booking ends the
    new template is deleted
    """
    name = user.username + "'s Copy of '" + old_template.name + "'"
    num_copies = ResourceTemplate.objects.filter(name__startswith=name).count()
    template = ResourceTemplate.objects.create(
        name=name if num_copies == 0 else name + " (" + str(num_copies) + ")",
        xml=old_template.xml,
        owner=user,
        lab=old_template.lab,
        description=old_template.description,
        public=False,
        temporary=True,
        copy_of=old_template
    )

    for old_network in old_template.networks.all():
        Network.objects.create(
            name=old_network.name,
            bundle=template,
            is_public=False
        )
    # We are assuming there is only one opnfv config per public resource template
    old_opnfv = template.opnfv_config.first()
    if old_opnfv:
        opnfv_config = OPNFVConfig.objects.create(
            installer=old_opnfv.installer,
            scenario=old_opnfv.installer,
            template=template,
            name=old_opnfv.installer,
        )
    # I am explicitly leaving opnfv_config.networks empty to avoid
    # problems with duplicated / shared networks. In the quick deploy,
    # there is never multiple networks anyway. This may have to change in the future

    for old_config in old_template.getConfigs():
        config = ResourceConfiguration.objects.create(
            profile=old_config.profile,
            image=image,
            template=template,
            is_head_node=old_config.is_head_node
        )

        for old_iface_config in old_config.interface_configs.all():
            iface_config = InterfaceConfiguration.objects.create(
                profile=old_iface_config.profile,
                resource_config=config
            )

            for old_connection in old_iface_config.connections.all():
                iface_config.connections.add(NetworkConnection.objects.create(
                    network=template.networks.get(name=old_connection.network.name),
                    vlan_is_tagged=old_connection.vlan_is_tagged
                ))

        for old_res_opnfv in old_config.resource_opnfv_config.all():
            if old_opnfv:
                ResourceOPNFVConfig.objects.create(
                    role=old_opnfv.role,
                    resource_config=config,
                    opnfv_config=opnfv_config
                )
    return template


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
    return ResourceOPNFVConfig.objects.create(
        role=role,
        host_config=hostconfig,
        opnfv_config=opnfvconfig
    )


def generate_resource_bundle(template):
    resource_manager = ResourceManager.getInstance()
    resource_bundle = resource_manager.instantiateTemplate(template)
    return resource_bundle


def check_invariants(request, **kwargs):
    # TODO: This should really happen in the BookingForm validation methods
    installer = kwargs['installer']
    image = kwargs['image']
    scenario = kwargs['scenario']
    lab = kwargs['lab']
    length = kwargs['length']
    # check that image os is compatible with installer
    if installer in image.os.sup_installers.all():
        # if installer not here, we can omit that and not check for scenario
        if not scenario:
            raise ValidationError("An OPNFV Installer needs a scenario to be chosen to work properly")
        if scenario not in installer.sup_scenarios.all():
            raise ValidationError("The chosen installer does not support the chosen scenario")
    if image.from_lab != lab:
        raise ValidationError("The chosen image is not available at the chosen hosting lab")
    # TODO
    # if image.host_type != host_profile:
    #    raise ValidationError("The chosen image is not available for the chosen host type")
    if not image.public and image.owner != request.user:
        raise ValidationError("You are not the owner of the chosen private image")
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

    resource_template = update_template(resource_template, image, hostname, request.user)

    # if no installer provided, just create blank host
    opnfv_config = None
    if installer:
        hconf = resource_template.getConfigs()[0]
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
            'host_profile': str(image.host_type.id),
            'name': image.name
        }

    resource_filter = {}
    templates = ResourceTemplate.objects.filter(Q(public=True) | Q(owner=user))
    for rt in templates:
        profiles = [conf.profile for conf in rt.getConfigs()]
        resource_filter["resource_" + str(rt.id)] = [str(p.id) for p in profiles]

    return {
        'installer_filter': json.dumps(installer_filter),
        'scenario_filter': json.dumps(scenario_filter),
        'image_filter': json.dumps(image_filter),
        'resource_profile_map': json.dumps(resource_filter),
    }
