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

from account.models import Downtime, Lab
from booking.models import Booking
from liblaas.views import booking_booking_status
from django.http import HttpResponse, JsonResponse

class BookingView(TemplateView):
    template_name = "booking/booking_detail.html"

    def get_context_data(self, **kwargs):
        booking = get_object_or_404(Booking, id=self.kwargs['booking_id'])
        title = 'Booking Details'
        contact = Lab.objects.filter(name="UNH_IOL").first().contact_email
        downtime = Downtime.objects.filter(lab=booking.lab, start__lt=timezone.now, end__gt=timezone.now()).first()
        context = super(BookingView, self).get_context_data(**kwargs)
        context.update({
            'title': title,
            'booking': booking,
            'downtime': downtime,
            'contact_email': contact
        })
        return context


class BookingDeleteView(TemplateView):
    template_name = "booking/booking_delete.html"

    def get_context_data(self, **kwargs):
        booking = get_object_or_404(Booking, id=self.kwargs['booking_id'])
        title = 'Delete Booking'
        context = super(BookingDeleteView, self).get_context_data(**kwargs)
        context.update({'title': title, 'booking': booking})
        return context


def bookingDelete(request, booking_id):
    booking = get_object_or_404(Booking, id=booking_id)
    booking.delete()
    messages.add_message(request, messages.SUCCESS, 'Booking deleted')
    return redirect('../../../../')


class BookingListView(TemplateView):
    template_name = "booking/booking_list.html"

    def get_context_data(self, **kwargs):
        bookings = Booking.objects.filter(end__gte=timezone.now())
        title = 'Search Booking'
        context = super(BookingListView, self).get_context_data(**kwargs)
        context.update({'title': title, 'bookings': bookings})
        return context



def booking_detail_view(request, booking_id):
    if request.method == 'GET':
        user = None
        if request.user.is_authenticated:
            user = request.user
        else:
            return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

        booking = get_object_or_404(Booking, id=booking_id)
        statuses = []
        if booking.aggregateId:
            statuses = booking_booking_status(booking.aggregateId)
        allowed_users = set(list(booking.collaborators.all()))
        if (request.user.is_superuser):
            allowed_users.add(request.user)
        allowed_users.add(booking.owner)
        if user not in allowed_users:
            return render(request, "dashboard/login.html", {'title': 'This page is private'})
        
        context = {
            'title': 'Booking Details',
            'booking': booking,
            'status': statuses,
            'collab_string': ', '.join(map(str, booking.collaborators.all()))
        }

        return render(
            request,
            "booking/booking_detail.html",
            context
        )
    
    if request.method == 'POST':
        return update_booking_status(request)
    
    return HttpResponse(status=405)

def update_booking_status(request):
    if request.method != "POST":
        return HttpResponse(status=405)

    data = json.loads(request.body.decode('utf-8'))
    agg_id = data["agg_id"]

    response = booking_booking_status(agg_id)

    if (response):
        return JsonResponse(status=200, data=response)

    return HttpResponse(status=500)

