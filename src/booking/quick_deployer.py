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
    Vlan,
    Host,
    HostProfile,
    HostConfiguration,
    GenericResource,
    GenericHost,
    GenericInterface,
    OPNFVRole,
    OPNFVConfig
)
from resource_inventory.resource_manager import ResourceManager
from booking.models import Booking
from dashboard.exceptions import (
    InvalidHostnameException,
    ResourceAvailabilityException,
    ModelValidationException
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


def create_from_form(form, request):
    quick_booking_id = str(uuid.uuid4())

    host_field = form.cleaned_data['filter_field']
    host_json = json.loads(host_field)
    purpose_field = form.cleaned_data['purpose']
    project_field = form.cleaned_data['project']
    users_field = form.cleaned_data['users']
    host_name = form.cleaned_data['hostname']
    length = form.cleaned_data['length']

    image = form.cleaned_data['image']
    scenario = form.cleaned_data['scenario']
    installer = form.cleaned_data['installer']

    # get all initial info we need to validate
    lab_dict = host_json['labs'][0]
    lab_id = list(lab_dict.keys())[0]
    lab_user_id = int(lab_id.split("_")[-1])
    lab = Lab.objects.get(lab_user__id=lab_user_id)

    host_dict = host_json['hosts'][0]
    profile_id = list(host_dict.keys())[0]
    profile_id = int(profile_id.split("_")[-1])
    profile = HostProfile.objects.get(id=profile_id)

    # check validity of field data before trying to apply to models
    if not lab:
        raise LabDNE("Lab with provided ID does not exist")
    if not profile:
        raise HostProfileDNE("Host type with provided ID does not exist")

    # check that hostname is valid
    if not re.match(r"(?=^.{1,253}$)(^([A-Za-z0-9-_]{1,62}\.)*[A-Za-z0-9-_]{1,63})$", host_name):
        raise InvalidHostnameException("Hostname must comply to RFC 952 and all extensions to it until this point")
    # check that image os is compatible with installer
    if installer in image.os.sup_installers.all():
        # if installer not here, we can omit that and not check for scenario
        if not scenario:
            raise IncompatibleScenarioForInstaller("An OPNFV Installer needs a scenario to be chosen to work properly")
        if scenario not in installer.sup_scenarios.all():
            raise IncompatibleScenarioForInstaller("The chosen installer does not support the chosen scenario")
    if image.from_lab != lab:
        raise ImageNotAvailableAtLab("The chosen image is not available at the chosen hosting lab")
    if image.host_type != profile:
        raise IncompatibleImageForHost("The chosen image is not available for the chosen host type")
    if not image.public and image.owner != request.user:
        raise ImageOwnershipInvalid("You are not the owner of the chosen private image")

    # check if host type is available
    # ResourceManager.getInstance().acquireHost(ghost, lab.name)
    available_host_types = ResourceManager.getInstance().getAvailableHostTypes(lab)
    if profile not in available_host_types:
        # TODO: handle deleting generic resource in this instance along with grb
        raise HostNotAvailable("Could not book selected host due to changed availability. Try again later")

    # check if any hosts with profile at lab are still available
    hostset = Host.objects.filter(lab=lab, profile=profile).filter(booked=False).filter(working=True)
    if not hostset.first():
        raise HostNotAvailable("Couldn't find any matching unbooked hosts")

    # generate GenericResourceBundle
    if len(host_json['labs']) != 1:
        raise NoLabSelectedError("No lab was selected")

    grbundle = GenericResourceBundle(owner=request.user)
    grbundle.lab = lab
    grbundle.name = "grbundle for quick booking with uid " + quick_booking_id
    grbundle.description = "grbundle created for quick-deploy booking"
    grbundle.save()

    # generate GenericResource, GenericHost
    gresource = GenericResource(bundle=grbundle, name=host_name)
    gresource.save()

    ghost = GenericHost()
    ghost.resource = gresource
    ghost.profile = profile
    ghost.save()

    # generate config bundle
    cbundle = ConfigBundle()
    cbundle.owner = request.user
    cbundle.name = "configbundle for quick booking  with uid " + quick_booking_id
    cbundle.description = "configbundle created for quick-deploy booking"
    cbundle.bundle = grbundle
    cbundle.save()

    # generate OPNFVConfig pointing to cbundle
    if installer:
        opnfvconfig = OPNFVConfig()
        opnfvconfig.scenario = scenario
        opnfvconfig.installer = installer
        opnfvconfig.bundle = cbundle
        opnfvconfig.save()

    # generate HostConfiguration pointing to cbundle
    hconf = HostConfiguration()
    hconf.host = ghost
    hconf.image = image
    hconf.opnfvRole = OPNFVRole.objects.get(name="Jumphost")
    if not hconf.opnfvRole:
        raise OPNFVRoleDNE("No jumphost role was found")
    hconf.bundle = cbundle
    hconf.save()

    # construct generic interfaces
    for interface_profile in profile.interfaceprofile.all():
        generic_interface = GenericInterface.objects.create(profile=interface_profile, host=ghost)
        generic_interface.save()
    ghost.save()

    # get vlan, assign to first interface
    publicnetwork = lab.vlan_manager.get_public_vlan()
    publicvlan = publicnetwork.vlan
    if not publicnetwork:
        raise NoRemainingPublicNetwork("No public networks were available for your pod")
    lab.vlan_manager.reserve_public_vlan(publicvlan)

    vlan = Vlan.objects.create(vlan_id=publicvlan, tagged=False, public=True)
    vlan.save()
    ghost.generic_interfaces.first().vlans.add(vlan)
    ghost.generic_interfaces.first().save()

    # generate resource bundle
    try:
        resource_bundle = ResourceManager.getInstance().convertResourceBundle(grbundle, config=cbundle)
    except ResourceAvailabilityException:
        raise ResourceAvailabilityException("Requested resources not available")
    except ModelValidationException:
        raise ModelValidationException("Encountered error while saving grbundle")

    # generate booking
    booking = Booking()
    booking.purpose = purpose_field
    booking.project = project_field
    booking.lab = lab
    booking.owner = request.user
    booking.start = timezone.now()
    booking.end = timezone.now() + timedelta(days=int(length))
    booking.resource = resource_bundle
    booking.pdf = ResourceManager().makePDF(booking.resource)
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
