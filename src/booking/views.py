##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib import messages, admin
import json
from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
from workflow.forms import BookingMetaForm

from account.models import Downtime, Lab, UserProfile
from booking.models import Booking
from liblaas.views import booking_booking_status, flavor_list_flavors, user_add_users
from django.http import HttpResponse, JsonResponse, HttpRequest
from django.contrib.auth.models import User

from liblaas.views import booking_ipmi_fqdn

from laas_dashboard.settings import HOST_DOMAIN, PROJECT
from booking.lib import resolve_hostname
from datetime import timedelta


def owner_action(action):
    """
    Decorator to verify that the request user is the booking owner and that the booking is not complete.
    Passes the entire booking object to the decorated function.
    Each function that is decorated by 'owner_action' needs to take an HttpRequest and a Booking id as arguments
    The decorator function will pass the queried Booking object (obtained from the id) to the action function, so there is no need to make a second query.
    """
    def decorator_function(request: HttpRequest, booking_id: int, **kwargs) -> HttpResponse:

        booking: Booking = Booking.objects.get(id=booking_id)
        user: User = request.user

        if booking.owner != user:
            return JsonResponse(status=403, data={"message": "Only the booking owner may perform this action!"})
        
        if booking.complete:
            return JsonResponse(status=403, data={"message": "This action can only be performed on an active booking!"})

        return action(request, booking_id, booking=booking)
    return decorator_function
class BookingView(TemplateView):
    template_name = "booking/booking_detail.html"

    def get_context_data(self, **kwargs):
        booking = get_object_or_404(Booking, id=self.kwargs["booking_id"])
        title = "Booking Details"
        contact = Lab.objects.filter(name="UNH_IOL").first().contact_email
        downtime = Downtime.objects.filter(
            lab=booking.lab, start__lt=timezone.now, end__gt=timezone.now()
        ).first()
        context = super(BookingView, self).get_context_data(**kwargs)
        context.update(
            {
                "title": title,
                "booking": booking,
                "downtime": downtime,
                "contact_email": contact,
            }
        )
        return context


class BookingDeleteView(TemplateView):
    template_name = "booking/booking_delete.html"

    def get_context_data(self, **kwargs):
        booking = get_object_or_404(Booking, id=self.kwargs["booking_id"])
        title = "Delete Booking"
        context = super(BookingDeleteView, self).get_context_data(**kwargs)
        context.update({"title": title, "booking": booking})
        return context


def bookingDelete(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.delete()
    messages.add_message(request, messages.SUCCESS, "Booking deleted")
    return redirect("../../../../")


class BookingListView(TemplateView):
    template_name = "booking/booking_list.html"

    def get_context_data(self, **kwargs):
        bookings = Booking.objects.filter(end__gte=timezone.now())
        title = "Search Booking"
        context = super(BookingListView, self).get_context_data(**kwargs)
        context.update({"title": title, "bookings": bookings})
        return context


def booking_detail_view(request, booking_id):
    if request.method == "GET":
        user = None
        if request.user.is_authenticated:
            user = request.user
        else:
            return render(
                request, "dashboard/login.html", {"title": "Authentication Required"}
            )

        booking = get_object_or_404(Booking, id=booking_id)
        statuses = []
        if booking.aggregateId:
            statuses = booking_booking_status(booking.aggregateId)
        allowed_users = set(list(booking.collaborators.all()))
        if request.user.is_superuser:
            allowed_users.add(request.user)
        allowed_users.add(booking.owner)
        if user not in allowed_users:
            return render(
                request, "dashboard/login.html", {"title": "This page is private"}
            )

        flavorlist = flavor_list_flavors(PROJECT)
        hosts = []
        host_ipmi_fqdns = {}
        if statuses:
            for host in statuses.get("template").get("hosts"):
                curr_host = {}
                curr_host["name"] = host.get("hostname")
                for flavor in flavorlist:
                    if host.get("flavor") == flavor.get("flavor_id"):
                        curr_host["flavor"] = flavor.get("name")
                        for image in flavor.get("images"):
                            if host.get("image") == image.get("image_id"):
                                curr_host["image"] = image.get("name")
                hosts.append(curr_host)

            for instance in statuses.get("instances"):
                access = statuses.get("instances").get(instance).get("assigned_host")
                host_ipmi_fqdns[access] = booking_ipmi_fqdn(instance)

        context = {
            "title": "Booking Details",
            "booking": booking,
            "status": statuses,
            "collab_string": ", ".join(map(str, booking.collaborators.all())),
            "contact_email": Lab.objects.filter(name="UNH_IOL").first().contact_email,
            "templatehosts": hosts,
            "ipmi_fqdns": host_ipmi_fqdns,
            "host_domain": HOST_DOMAIN,
            "form": BookingMetaForm(initial={}, user_initial=[], owner=request.user),
        }

        return render(request, "booking/booking_detail.html", context)

    if request.method == "POST":
        return update_booking_status(request)

    return HttpResponse(status=405)


def update_booking_status(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    data = json.loads(request.body.decode("utf-8"))
    agg_id = data["agg_id"]

    response = booking_booking_status(agg_id)

    if response:
        return JsonResponse(status=200, data=response)

    return HttpResponse(status=500)

def get_host_ip(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    data = json.loads(request.body.decode("utf-8"))
    server_name = data["server_name"]

    response = resolve_hostname(f"{server_name}.{HOST_DOMAIN}")

    if response:
        return JsonResponse(status=200, data=response, safe=False)

    return HttpResponse(status=500)

def manage_collaborators(request, booking_id) -> HttpResponse:

    booking: Booking = Booking.objects.get(id=booking_id)

    if request.user != booking.owner:
        return HttpResponse(status=401)

    if request.method == "GET":
        return JsonResponse({"collaborators": ", ".join(map(str, booking.collaborators.all()))}, status=200)

    if request.method == "POST":
        data: list[int] = json.loads(request.body.decode('utf-8'))
        profiles: list[UserProfile] = list(UserProfile.objects.filter(id__in=data))
        ipa_usernames: list[str] = list(map(lambda profile: profile.ipa_username, profiles))

        liblaas_collabs = user_add_users(booking.aggregateId, ipa_usernames)

        if liblaas_collabs:
            for profile in profiles:
                booking.collaborators.add(profile.user)
            booking.save()
        return JsonResponse({"collaborators": ", ".join(map(str, booking.collaborators.all()))}, status=200)

    if request.method == "DELETE":
        # Remove collabs - unimplemented
        return HttpResponse(status=501)

    return HttpResponse(status=405)

@owner_action
def extend_booking(request: HttpRequest, booking_id: int, **kwargs) -> HttpResponse:
    # booking kwarg is set in the decorator call, retreived from booking_id
    booking: Booking = kwargs["booking"]

    if request.method == "POST":
        days: int = json.loads(request.body.decode('utf-8'))["days"]
        if days > 0 and days <= booking.ext_days:
            booking.ext_days -= days
            booking.end += timedelta(days)
            booking.save()
        else:
            return HttpResponse(status=400)

        extensions_remaining = booking.ext_days

        # Jinja automically formats the datetime when the page is loaded for the first time. We aren't re-rendering the page so we need to do it manually
        # It is not a 100% match but it's close
        updated_end_time = booking.end.strftime("%B %-d, %Y, %-I:%M ") + ("a.m." if booking.end.strftime("%P") == "am" else "p.m.")
        return JsonResponse(status=200, data={"extensions_remaining": extensions_remaining, "updated_end_time": updated_end_time})

    return HttpResponse(status=405)

@owner_action
def request_extend_booking(request: HttpRequest, booking_id: int, **kwargs) -> HttpResponse:
    # unimplemented
    return HttpResponse(501)
    booking: Booking = kwargs["booking"]

    if request.method == "POST":
        post_data: dict = json.loads(request.body.decode('utf-8'))
        date: str = post_data["date"]
        reason: str = post_data["reason"]
    
        # todo - hit liblaas

        return HttpResponse(200)

    return HttpResponse(status=405)
