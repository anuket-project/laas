##############################################################################
# Copyright (c) 2016 Max Breitenfeldt and others.
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib import messages
from django.shortcuts import get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.views import View
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
from django.db.models import Q
from django.urls import reverse

from account.models import Downtime, Lab
from api.views import get_booking_status
from booking.models import Booking

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
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

    booking = get_object_or_404(Booking, id=booking_id)
    statuses = get_booking_status(booking)
    allowed_users = set(list(booking.collaborators.all()))
    allowed_users.add(booking.owner)
    if user not in allowed_users:
        return render(request, "dashboard/login.html", {'title': 'This page is private'})
    
    context = {
        'title': 'Booking Details',
        'booking': booking,
        'statuses': statuses,
        'collab_string': ', '.join(map(str, booking.collaborators.all()))
    }

    return render(
        request,
        "booking/booking_detail.html",
        context
    )
