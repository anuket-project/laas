##############################################################################
# Copyright (c) 2021 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from resource_inventory.models import (
    ResourceTemplate,
    Image,
    Server,
    ResourceBundle,
    ResourceProfile,
    InterfaceProfile,
    PhysicalNetwork,
    ResourceConfiguration,
    NetworkConnection,
    InterfaceConfiguration,
    Network,
    DiskProfile,
    CpuProfile,
    RamProfile,
    Interface,
    CloudInitFile,
)

import json
import sys
import inspect
import pydoc

from django.contrib.auth.models import User

from account.models import (
    Lab,
    PublicNetwork
)

from resource_inventory.resource_manager import ResourceManager
from resource_inventory.pdf_templater import PDFTemplater

from booking.quick_deployer import update_template

from datetime import timedelta

from django.utils import timezone

from booking.models import Booking
from notifier.manager import NotificationHandler
from api.models import JobFactory

from api.models import JobStatus, Job, GeneratedCloudConfig


def print_div():
    """
    Utility function for printing dividers, does nothing directly useful as a utility
    """
    print("=" * 68)


def book_host(owner_username, host_labid, lab_username, hostname, image_id, template_name, length_days=21, collaborator_usernames=[], purpose="internal", project="LaaS"):
    """
    creates a quick booking using the given host

    @owner_username is the simple username for the user who will own the resulting booking.
    Do not set this to a lab username!

    @image_id is the django id of the image in question, NOT the labid of the image.
    Query Image objects by their public status and compatible host types

    @host_labid is usually of the form `hpe3` or similar, is the labid of the Server (subtype of Resource) object

    @lab_username for iol is `unh_iol`, other labs will be documented here

    @hostname the hostname that the resulting host should have set

    @template_name the name of the (public, or user accessible) template to use for this booking

    @length_days how long the booking should be, no hard limit currently

    @collaborator_usernames a list of usernames for collaborators to the booking

    @purpose what this booking will be used for

    @project what project/group this booking is on behalf of or the owner represents
    """
    lab = Lab.objects.get(lab_user__username=lab_username)
    host = Server.objects.filter(lab=lab).get(labid=host_labid)
    if host.booked:
        print("Can't book host, already marked as booked")
        return
    else:
        host.booked = True
        host.save()

    template = ResourceTemplate.objects.filter(public=True).get(name=template_name)
    image = Image.objects.get(id=image_id)

    owner = User.objects.get(username=owner_username)

    new_template = update_template(template, image, hostname, owner)

    rmanager = ResourceManager.getInstance()

    vlan_map = rmanager.get_vlans(new_template)

    # only a single host so can reuse var for iter here
    resource_bundle = ResourceBundle.objects.create(template=new_template)
    res_configs = new_template.getConfigs()

    for config in res_configs:
        try:
            host.bundle = resource_bundle
            host.config = config
            rmanager.configureNetworking(resource_bundle, host, vlan_map)
            host.save()
        except Exception:
            host.booked = False
            host.save()
            print("Failed to book host due to error configuring it")
            return

    new_template.save()

    booking = Booking.objects.create(
        purpose=purpose,
        project=project,
        lab=lab,
        owner=owner,
        start=timezone.now(),
        end=timezone.now() + timedelta(days=int(length_days)),
        resource=resource_bundle,
        opnfv_config=None
    )

    booking.pdf = PDFTemplater.makePDF(booking)

    booking.save()

    for collaborator_username in collaborator_usernames:
        try:
            user = User.objects.get(username=collaborator_username)
            booking.collaborators.add(user)
        except Exception:
            print("couldn't add user with username ", collaborator_username)

    booking.save()

    JobFactory.makeCompleteJob(booking)
    NotificationHandler.notify_new_booking(booking)


def mark_working(host_labid, lab_username, working=True):
    """
    Mark a host working/not working so that it is either bookable or hidden in the dashboard.

    @host_labid is usually of the form `hpe3` or similar, is the labid of the Server (subtype of Resource) object

    @lab_username: param of the form `unh_iol` or similar

    @working: bool, whether by the end of execution the host should be considered working or not working
    """

    lab = Lab.objects.get(lab_user__username=lab_username)
    server = Server.objects.filter(lab=lab).get(labid=host_labid)
    print("changing server working status from ", server.working, "to", working)
    server.working = working
    server.save()


def mark_booked(host_labid, lab_username, booked=True):
    """
    Mark a host as booked/unbooked

    @host_labid is usually of the form `hpe3` or similar, is the labid of the Server (subtype of Resource) object

    @lab_username: param of the form `unh_iol` or similar

    @working: bool, whether by the end of execution the host should be considered booked or not booked
    """

    lab = Lab.objects.get(lab_user__username=lab_username)
    server = Server.objects.filter(lab=lab).get(labid=host_labid)
    print("changing server booked status from ", server.booked, "to", booked)
    server.booked = booked
    server.save()


def get_host(host_labid, lab_username):
    """
    Returns host filtered by lab and then unique id within lab

    @host_labid is usually of the form `hpe3` or similar, is the labid of the Server (subtype of Resource) object

    @lab_username: param of the form `unh_iol` or similar
    """
    lab = Lab.objects.get(lab_user__username=lab_username)
    return Server.objects.filter(lab=lab).get(labid=host_labid)


def get_info(host_labid, lab_username):
    """
    Returns various information on the host queried by the given parameters

    @host_labid is usually of the form `hpe3` or similar, is the labid of the Server (subtype of Resource) object

    @lab_username: param of the form `unh_iol` or similar
    """
    info = {}
    host = get_host(host_labid, lab_username)
    info['host_labid'] = host_labid
    info['booked'] = host.booked
    info['working'] = host.working
    info['profile'] = str(host.profile)
    if host.bundle:
        binfo = {}
        info['bundle'] = binfo
    if host.config:
        cinfo = {}
        info['config'] = cinfo

    return info


def map_cntt_interfaces(labid: str):
    """
    Use this during cntt migrations, call it with a host labid and it will change profiles for this host
    as well as mapping its interfaces across. interface ens1f2 should have the mac address of interface eno50
    as an invariant before calling this function
    """
    host = get_host(labid, "unh_iol")
    host.profile = ResourceProfile.objects.get(name="HPE x86 CNTT")
    host.save()
    host = get_host(labid, "unh_iol")

    for iface in host.interfaces.all():
        new_ifprofile = None
        if iface.profile.name == "ens1f2":
            new_ifprofile = InterfaceProfile.objects.get(host=host.profile, name="eno50")
        else:
            new_ifprofile = InterfaceProfile.objects.get(host=host.profile, name=iface.profile.name)

        iface.profile = new_ifprofile

        iface.save()


def detect_leaked_hosts(labid="unh_iol"):
    """
    Use this to try to detect leaked hosts.
    These hosts may still be in the process of unprovisioning,
    but if they are not (or unprovisioning is frozen) then
    these hosts are instead leaked
    """
    working_servers = Server.objects.filter(working=True, lab__lab_user__username=labid)
    booked = working_servers.filter(booked=True)
    filtered = booked
    print_div()
    print("In use now:")
    for booking in Booking.objects.filter(end__gte=timezone.now()):
        res_for_booking = booking.resource.get_resources()
        print(res_for_booking)
        for resource in res_for_booking:
            filtered = filtered.exclude(id=resource.id)
    print_div()
    print("Possibly leaked:")
    for host in filtered:
        print(host)
    print_div()
    return filtered


def booking_for_host(host_labid: str, lab_username="unh_iol"):
    """
    Returns the booking that this server is a part of, if any.
    Fails with an exception if no such booking exists

    @host_labid is usually of the form `hpe3` or similar, is the labid of the Server (subtype of Resource) object

    @lab_username: param of the form `unh_iol` or similar
    """
    server = Server.objects.get(lab__lab_user__username=lab_username, labid=host_labid)
    booking = server.bundle.booking_set.first()
    print_div()
    print(booking)
    print("id:", booking.id)
    print("owner:", booking.owner)
    print("job (id):", booking.job, "(" + str(booking.job.id) + ")")
    print_div()
    return booking


def force_release_booking(booking_id: int):
    """
    Takes a booking id and forces the booking to end whether or not the tasks have
    completed normally.

    Use with caution! Hosts may or may not be released depending on other underlying issues

    @booking_id: the id of the Booking object to be released
    """
    booking = Booking.objects.get(id=booking_id)
    job = booking.job
    tasks = job.get_tasklist()
    for task in tasks:
        task.status = JobStatus.DONE
        task.save()


def free_leaked_public_vlans(safety_buffer_days=2):
    for lab in Lab.objects.all():
        current_booking_set = Booking.objects.filter(end__gte=timezone.now() + timedelta(days=safety_buffer_days))

        marked_nets = set()

        for booking in current_booking_set:
            for network in get_network_metadata(booking.id):
                marked_nets.add(network["vlan_id"])

        for net in PublicNetwork.objects.filter(lab=lab).filter(in_use=True):
            if net.vlan not in marked_nets:
                lab.vlan_manager.release_public_vlan(net.vlan)


def get_network_metadata(booking_id: int):
    """
    Takes a booking id and prints all (known) networks that are owned by it.
    Returns an object of the form {<network name>: {"vlan_id": int, "netname": str <network name>, "public": bool <whether network is public/routable}}

    @booking_id: the id of the Booking object to be queried
    """
    booking = Booking.objects.get(id=booking_id)
    bundle = booking.resource
    pnets = PhysicalNetwork.objects.filter(bundle=bundle).all()
    metadata = {}
    for pnet in pnets:
        net = pnet.generic_network
        mdata = {"vlan_id": pnet.vlan_id, "netname": net.name, "public": net.is_public}
        metadata[net.name] = mdata
    return metadata


def print_dict_pretty(a_dict):
    """
    admin_utils internal function
    """

    print(json.dumps(a_dict, sort_keys=True, indent=4))


def add_profile(data):
    """
    Used for adding a host profile to the dashboard

    schema (of dict passed as "data" param):
    {
        "name": str
        "description": str
        "labs": [
            str (lab username)
        ]
        "disks": {
            <diskname> : {
                capacity: int (GiB)
                media_type: str ("SSD" or "HDD")
                interface: str ("sata", "sas", "ssd", "nvme", "scsi", or "iscsi")
            }
        }
        interfaces: {
            <intname>: {
                "speed": int (mbit)
                "nic_type": str ("onboard" or "pcie")
                "order": int (compared to the other interfaces, indicates the "order" that the ports are laid out)
            }
        }
        cpus: {
            cores: int (hardware threads count)
            architecture: str (x86_64" or "aarch64")
            cpus: int (number of sockets)
            cflags: str
        }
        ram: {
            amount: int (GiB)
            channels: int
        }
    }
    """
    base_profile = ResourceProfile.objects.create(name=data['name'], description=data['description'])
    base_profile.save()

    for lab_username in data['labs']:
        lab = Lab.objects.get(lab_user__username=lab_username)

        base_profile.labs.add(lab)
        base_profile.save()

    for diskname in data['disks'].keys():
        disk = data['disks'][diskname]

        disk_profile = DiskProfile.objects.create(name=diskname, size=disk['capacity'], media_type=disk['media_type'], interface=disk['interface'], host=base_profile)
        disk_profile.save()

    for ifacename in data['interfaces'].keys():
        iface = data['interfaces'][ifacename]

        iface_profile = InterfaceProfile.objects.create(name=ifacename, speed=iface['speed'], nic_type=iface['nic_type'], order=iface['order'], host=base_profile)
        iface_profile.save()

    cpu = data['cpus']
    cpu_prof = CpuProfile.objects.create(cores=cpu['cores'], architecture=cpu['architecture'], cpus=cpu['cpus'], cflags=cpu['cflags'], host=base_profile)
    cpu_prof.save()

    ram_prof = RamProfile.objects.create(amount=data['ram']['amount'], channels=data['ram']['channels'], host=base_profile)
    ram_prof.save()


def make_default_template(resource_profile, image_id=None, template_name=None, connected_interface_names=None, interfaces_tagged=False, connected_interface_tagged=False, owner_username="root", lab_username="unh_iol", public=True, temporary=False, description=""):
    """
    Do not call this function without reading the related source code, it may have unintended effects.

    Used for creating a default template from some host profile
    """

    if not resource_profile:
        raise Exception("No viable continuation from none resource_profile")

    if not template_name:
        template_name = resource_profile.name

    if not connected_interface_names:
        connected_interface_names = [InterfaceProfile.objects.filter(host=resource_profile).first().name]
        print("setting connected interface names to", connected_interface_names)

    if not image_id:
        image_id = Image.objects.filter(host_type=resource_profile).first().id

    image = Image.objects.get(id=image_id)

    base = ResourceTemplate.objects.create(
        name=template_name,
        xml="",
        owner=User.objects.get(username=owner_username),
        lab=Lab.objects.get(lab_user__username=lab_username), description=description,
        public=public, temporary=temporary, copy_of=None)

    rconf = ResourceConfiguration.objects.create(profile=resource_profile, image=image, template=base, is_head_node=True, name="opnfv_host")
    rconf.save()

    connected_interfaces = []

    for iface_prof in InterfaceProfile.objects.filter(host=resource_profile).all():
        iface_conf = InterfaceConfiguration.objects.create(profile=iface_prof, resource_config=rconf)

        if iface_prof.name in connected_interface_names:
            connected_interfaces.append(iface_conf)

    network = Network.objects.create(name="public", bundle=base, is_public=True)

    for iface in connected_interfaces:
        connection = NetworkConnection.objects.create(network=network, vlan_is_tagged=interfaces_tagged)
        connection.save()

        iface.connections.add(connection)
        print("adding connection to iface ", iface)
        iface.save()
        connection.save()


def add_server(profile, name, interfaces, lab_username="unh_iol", vendor="unknown", model="unknown"):
    """
    Used to enroll a new host of some profile

    @profile: the ResourceProfile in question (by reference to a model object)

    @name: the unique name of the server, currently indistinct from labid

    @interfaces: interfaces should be dict from interface name (eg ens1f0) to dict of schema:
        {
            mac_address: <mac addr>,
            bus_addr: <bus addr>, //this field is optional, "" is default
        }

    @lab_username: username of the lab to be added to

    @vendor: vendor name of the host, such as "HPE" or "Gigabyte"

    @model: specific model of the host, such as "DL380 Gen 9"

    """
    server = Server.objects.create(
        bundle=None,
        profile=profile,
        config=None,
        working=True,
        vendor=vendor,
        model=model,
        labid=name,
        lab=Lab.objects.get(lab_user__username=lab_username),
        name=name,
        booked=False)

    for iface_prof in InterfaceProfile.objects.filter(host=profile).all():
        mac_addr = interfaces[iface_prof.name]["mac_address"]
        bus_addr = "unknown"
        if "bus_addr" in interfaces[iface_prof.name].keys():
            bus_addr = interfaces[iface_prof.name]["bus_addr"]

        iface = Interface.objects.create(acts_as=None, profile=iface_prof, mac_address=mac_addr, bus_address=bus_addr)
        iface.save()

        server.interfaces.add(iface)
        server.save()


def extend_booking(booking_id, days=0, hours=0, minutes=0, weeks=0):
    """
    Extend a booking by n <days, hours, minutes, weeks>

    @booking_id: id of the booking

    @days/@hours/@minutes/@weeks: the cumulative amount of delta to add to the length of the booking
    """

    booking = Booking.objects.get(id=booking_id)
    booking.end = booking.end + timedelta(days=days, hours=hours, minutes=minutes, weeks=weeks)
    booking.save()


def regenerate_cloud_configs(booking_id):
    b = Booking.objects.get(id=booking_id)
    for res in b.resource.get_resources():
        res.config.cloud_init_files.set(res.config.cloud_init_files.filter(generated=False))  # careful!
        res.config.save()
        cif = GeneratedCloudConfig.objects.create(resource_id=res.labid, booking=b, rconfig=res.config)
        cif.save()
        cif = CloudInitFile.create(priority=0, text=cif.serialize())
        cif.save()
        res.config.cloud_init_files.add(cif)
        res.config.save()


def set_job_new(job_id):
    j = Job.objects.get(id=job_id)
    b = j.booking
    regenerate_cloud_configs(b.id)
    for task in j.get_tasklist():
        task.status = JobStatus.NEW
        task.save()
    j.status = JobStatus.NEW
    j.save()


def docs(function=None, fulltext=False):
    """
    Print documentation for a given function in admin_utils.
    Call without arguments for more information
    """

    fn = None

    if isinstance(function, str):
        try:
            fn = globals()[function]
        except KeyError:
            print("Couldn't find a function by the given name")
            return
    elif callable(function):
        fn = function
    else:
        print("docs(function: callable | str, fulltext: bool) was called with a 'function' that was neither callable nor a string name of a function")
        print("usage: docs('some_function_in_admin_utils', fulltext=True)")
        print("The 'fulltext' argument is used to choose if you want the complete source of the function printed. If this argument is false then you will only see the pydoc rendered documentation for the function")
        return

    if not fn:
        print("couldn't find a function by that name")

    if not fulltext:
        print("Pydoc documents the function as such:")
        print(pydoc.render_doc(fn))
    else:
        print("The full source of the function is this:")
        print(inspect.getsource(fn))


def admin_functions():
    """
    List functions available to call within admin_utils
    """

    return [name for name, func in inspect.getmembers(sys.modules[__name__]) if (inspect.isfunction(func) and func.__module__ == __name__)]


print("Hint: call `docs(<function name>)` or `admin_functions()` for help on using the admin utils")
print("docs(<function name>) displays documentation on a given function")
print("admin_functions() lists all functions available to call within this module")
