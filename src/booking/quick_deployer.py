##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


import json
import uuid
import re
from django.db.models import Q
from django.contrib.auth.models import User
from datetime import timedelta
from django.utils import timezone
from account.models import Lab

from resource_inventory.models import (
    Installer,
    Image,
    GenericResourceBundle,
    ConfigBundle,
    Host,
    HostProfile,
    HostConfiguration,
    GenericResource,
    GenericHost,
    GenericInterface,
    OPNFVRole,
    OPNFVConfig,
    Network,
    NetworkConnection,
    NetworkRole
)
from resource_inventory.resource_manager import ResourceManager
from resource_inventory.pdf_templater import PDFTemplater
from notifier.manager import NotificationHandler
from booking.models import Booking
from dashboard.exceptions import (
    InvalidHostnameException,
    ResourceAvailabilityException,
    ModelValidationException,
    BookingLengthException
)
from api.models import JobFactory


# model validity exceptions
class IncompatibleInstallerForOS(Exception):
    pass


class IncompatibleScenarioForInstaller(Exception):
    pass


class IncompatibleImageForHost(Exception):
    pass


class ImageOwnershipInvalid(Exception):
    pass


class ImageNotAvailableAtLab(Exception):
    pass


class LabDNE(Exception):
    pass


class HostProfileDNE(Exception):
    pass


class HostNotAvailable(Exception):
    pass


class NoLabSelectedError(Exception):
    pass


class OPNFVRoleDNE(Exception):
    pass


class NoRemainingPublicNetwork(Exception):
    pass


def parse_host_field(host_field_contents):
    host_json = json.loads(host_field_contents)
    lab_dict = host_json['labs'][0]
    lab_id = list(lab_dict.keys())[0]
    lab_user_id = int(lab_id.split("_")[-1])
    lab = Lab.objects.get(lab_user__id=lab_user_id)

    host_dict = host_json['hosts'][0]
    profile_id = list(host_dict.keys())[0]
    profile_id = int(profile_id.split("_")[-1])
    profile = HostProfile.objects.get(id=profile_id)

    # check validity of field data before trying to apply to models
    if len(host_json['labs']) != 1:
        raise NoLabSelectedError("No lab was selected")
    if not lab:
        raise LabDNE("Lab with provided ID does not exist")
    if not profile:
        raise HostProfileDNE("Host type with provided ID does not exist")

    return lab, profile


def check_available_matching_host(lab, hostprofile):
    available_host_types = ResourceManager.getInstance().getAvailableHostTypes(lab)
    if hostprofile not in available_host_types:
        # TODO: handle deleting generic resource in this instance along with grb
        raise HostNotAvailable('Requested host type is not available. Please try again later. Host availability can be viewed in the "Hosts" tab to the left.')

    hostset = Host.objects.filter(lab=lab, profile=hostprofile).filter(booked=False).filter(working=True)
    if not hostset.exists():
        raise HostNotAvailable("Couldn't find any matching unbooked hosts")

    return True


def generate_grb(owner, lab, common_id):
    grbundle = GenericResourceBundle(owner=owner)
    grbundle.lab = lab
    grbundle.name = "grbundle for quick booking with uid " + common_id
    grbundle.description = "grbundle created for quick-deploy booking"
    grbundle.save()

    return grbundle


def generate_gresource(bundle, hostname):
    if not re.match(r"(?=^.{1,253}$)(^([A-Za-z0-9-_]{1,62}\.)*[A-Za-z0-9-_]{1,63})$", hostname):
        raise InvalidHostnameException("Hostname must comply to RFC 952 and all extensions to it until this point")
    gresource = GenericResource(bundle=bundle, name=hostname)
    gresource.save()

    return gresource


def generate_ghost(generic_resource, host_profile):
    ghost = GenericHost()
    ghost.resource = generic_resource
    ghost.profile = host_profile
    ghost.save()

    return ghost


def generate_config_bundle(owner, common_id, grbundle):
    cbundle = ConfigBundle()
    cbundle.owner = owner
    cbundle.name = "configbundle for quick booking with uid " + common_id
    cbundle.description = "configbundle created for quick-deploy booking"
    cbundle.bundle = grbundle
    cbundle.save()

    return cbundle


def generate_opnfvconfig(scenario, installer, config_bundle):
    opnfvconfig = OPNFVConfig()
    opnfvconfig.scenario = scenario
    opnfvconfig.installer = installer
    opnfvconfig.bundle = config_bundle
    opnfvconfig.save()

    return opnfvconfig


def generate_hostconfig(generic_host, image, config_bundle):
    hconf = HostConfiguration()
    hconf.host = generic_host
    hconf.image = image

    opnfvrole = OPNFVRole.objects.get(name="Jumphost")
    if not opnfvrole:
        raise OPNFVRoleDNE("No jumphost role was found.")

    hconf.opnfvRole = opnfvrole
    hconf.bundle = config_bundle
    hconf.save()

    return hconf


def generate_resource_bundle(generic_resource_bundle, config_bundle):  # warning: requires cleanup
    try:
        resource_manager = ResourceManager.getInstance()
        resource_bundle = resource_manager.convertResourceBundle(generic_resource_bundle, config=config_bundle)
        return resource_bundle
    except ResourceAvailabilityException:
        raise ResourceAvailabilityException("Requested resources not available")
    except ModelValidationException:
        raise ModelValidationException("Encountered error while saving grbundle")


def check_invariants(request, **kwargs):
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
            raise IncompatibleScenarioForInstaller("An OPNFV Installer needs a scenario to be chosen to work properly")
        if scenario not in installer.sup_scenarios.all():
            raise IncompatibleScenarioForInstaller("The chosen installer does not support the chosen scenario")
    if image.from_lab != lab:
        raise ImageNotAvailableAtLab("The chosen image is not available at the chosen hosting lab")
    if image.host_type != host_profile:
        raise IncompatibleImageForHost("The chosen image is not available for the chosen host type")
    if not image.public and image.owner != request.user:
        raise ImageOwnershipInvalid("You are not the owner of the chosen private image")
    if length < 1 or length > 21:
        raise BookingLengthException("Booking must be between 1 and 21 days long")


def configure_networking(grb, config):
    # create network
    net = Network.objects.create(name="public", bundle=grb, is_public=True)
    # connect network to generic host
    grb.getHosts()[0].generic_interfaces.first().connections.add(
        NetworkConnection.objects.create(network=net, vlan_is_tagged=False)
    )
    # asign network role
    role = NetworkRole.objects.create(name="public", network=net)
    opnfv_config = config.opnfv_config.first()
    if opnfv_config:
        opnfv_config.networks.add(role)


def create_from_form(form, request):
    quick_booking_id = str(uuid.uuid4())

    host_field = form.cleaned_data['filter_field']
    purpose_field = form.cleaned_data['purpose']
    project_field = form.cleaned_data['project']
    users_field = form.cleaned_data['users']
    hostname = form.cleaned_data['hostname']
    length = form.cleaned_data['length']

    image = form.cleaned_data['image']
    scenario = form.cleaned_data['scenario']
    installer = form.cleaned_data['installer']

    lab, host_profile = parse_host_field(host_field)
    data = form.cleaned_data
    data['lab'] = lab
    data['host_profile'] = host_profile
    check_invariants(request, **data)

    check_available_matching_host(lab, host_profile)  # requires cleanup if failure after this point

    grbundle = generate_grb(request.user, lab, quick_booking_id)

    gresource = generate_gresource(grbundle, hostname)

    ghost = generate_ghost(gresource, host_profile)

    cbundle = generate_config_bundle(request.user, quick_booking_id, grbundle)

    # if no installer provided, just create blank host
    if installer:
        generate_opnfvconfig(scenario, installer, cbundle)

    generate_hostconfig(ghost, image, cbundle)

    # construct generic interfaces
    for interface_profile in host_profile.interfaceprofile.all():
        generic_interface = GenericInterface.objects.create(profile=interface_profile, host=ghost)
        generic_interface.save()

    configure_networking(grbundle, cbundle)

    # generate resource bundle
    resource_bundle = generate_resource_bundle(grbundle, cbundle)

    # generate booking
    booking = Booking()
    booking.purpose = purpose_field
    booking.project = project_field
    booking.lab = lab
    booking.owner = request.user
    booking.start = timezone.now()
    booking.end = timezone.now() + timedelta(days=int(length))
    booking.resource = resource_bundle
    booking.pdf = PDFTemplater.makePDF(booking.resource)
    booking.config_bundle = cbundle
    booking.save()
    users_field = users_field[2:-2]
    if users_field:  # may be empty after split, if no collaborators entered
        users_field = json.loads(users_field)
        for collaborator in users_field:
            user = User.objects.get(id=collaborator['id'])
            booking.collaborators.add(user)
        booking.save()

    # generate job
    JobFactory.makeCompleteJob(booking)
    NotificationHandler.notify_new_booking(booking)


def drop_filter(user):
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
        image_filter[image.id] = {}
        image_filter[image.id]['lab'] = 'lab_' + str(image.from_lab.lab_user.id)
        image_filter[image.id]['host_profile'] = 'host_' + str(image.host_type.id)
        image_filter[image.id]['name'] = image.name

    return {'installer_filter': json.dumps(installer_filter),
            'scenario_filter': json.dumps(scenario_filter),
            'image_filter': json.dumps(image_filter)}
