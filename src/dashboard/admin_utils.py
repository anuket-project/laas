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
    RamProfile
)

import json

from django.contrib.auth.models import User

from account.models import Lab

from resource_inventory.resource_manager import ResourceManager
from resource_inventory.pdf_templater import PDFTemplater

from booking.quick_deployer import update_template

from datetime import timedelta

from django.utils import timezone

from booking.models import Booking
from notifier.manager import NotificationHandler
from api.models import JobFactory

from api.models import JobStatus


def print_div():
    print("====================================================================")


def book_host(owner_username, host_labid, lab_username, hostname, image_id, template_name, length_days=21, collaborator_usernames=[], purpose="internal", project="LaaS"):
    """
    creates a quick booking using the given host
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
    lab = Lab.objects.get(lab_user__username=lab_username)
    server = Server.objects.filter(lab=lab).get(labid=host_labid)
    print("changing server working status from ", server.working, "to", working)
    server.working = working
    server.save()


def mark_booked(host_labid, lab_username, booked=True):
    lab = Lab.objects.get(lab_user__username=lab_username)
    server = Server.objects.filter(lab=lab).get(labid=host_labid)
    print("changing server booked status from ", server.booked, "to", booked)
    server.booked = booked
    server.save()


# returns host filtered by lab and then unique id within lab
def get_host(host_labid, lab_username):
    lab = Lab.objects.get(lab_user__username=lab_username)
    return Server.objects.filter(lab=lab).get(labid=host_labid)


def get_info(host_labid, lab_username):
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


def booking_for_host(host_labid: str, labid="unh_iol"):
    server = Server.objects.get(lab__lab_user__username=labid, labid=host_labid)
    booking = server.bundle.booking_set.first()
    print_div()
    print(booking)
    print("id:", booking.id)
    print("owner:", booking.owner)
    print("job (id):", booking.job, "(" + str(booking.job.id) + ")")
    print_div()
    return booking


def force_release_booking(booking_id):
    booking = Booking.objects.get(id=booking_id)
    job = booking.job
    tasks = job.get_tasklist()
    for task in tasks:
        task.status = JobStatus.DONE
        task.save()


def get_network_metadata(booking_id: int):
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
    print(json.dumps(a_dict, sort_keys=True, indent=4))


"""
schema:
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


def add_profile(data):
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
