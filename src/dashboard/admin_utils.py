from resource_inventory.models import (
    ResourceTemplate,
    Image,
    Server,
    ResourceBundle,
)

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


"""
creates a quick booking using the given host
"""


def book_host(owner_username, host_labid, lab_username, hostname, image_id, template_name, length_days=21, collaborator_usernames=[], purpose="internal", project="LaaS"):
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
