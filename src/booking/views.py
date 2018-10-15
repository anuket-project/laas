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
from django.http import JsonResponse
from django.urls import reverse
from django.utils import timezone
from django.views import View
from django.views.generic import FormView
from django.views.generic import TemplateView
from django.shortcuts import redirect, render
import json

from booking.forms import BookingForm, BookingEditForm
from resource_inventory.models import ResourceBundle
from resource_inventory.resource_manager import ResourceManager
from booking.models import Booking, Installer, Opsys
from booking.stats import StatisticsManager


def drop_filter(context):
    installer_filter = {}
    for os in Opsys.objects.all():
        installer_filter[os.id] = []
        for installer in os.sup_installers.all():
            installer_filter[os.id].append(installer.id)

    scenario_filter = {}
    for installer in Installer.objects.all():
        scenario_filter[installer.id] = []
        for scenario in installer.sup_scenarios.all():
            scenario_filter[installer.id].append(scenario.id)

    context.update({'installer_filter': json.dumps(installer_filter), 'scenario_filter': json.dumps(scenario_filter)})


class BookingFormView(FormView):
    template_name = "booking/booking_calendar.html"
    form_class = BookingForm

    def dispatch(self, request, *args, **kwargs):
        self.resource = get_object_or_404(ResourceBundle, id=self.kwargs['resource_id'])
        return super(BookingFormView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        title = 'Booking: ' + str(self.resource.id)
        context = super(BookingFormView, self).get_context_data(**kwargs)
        context.update({'title': title, 'resource': self.resource})

        drop_filter(context)

        return context

    def get_success_url(self):
        return reverse('booking:create', kwargs=self.kwargs)

    def form_valid(self, form):
        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR,
                                 'You need to be logged in to book a Pod.')
            return super(BookingFormView, self).form_invalid(form)

        if form.cleaned_data['end'] - form.cleaned_data['start'] > timezone.timedelta(days=21):
            messages.add_message(self.request, messages.ERROR,
                                 'Bookings can be no more than 3 weeks long.')
            return super(BookingFormView, self).form_invalid(form)

        user = self.request.user
        booking = Booking(start=form.cleaned_data['start'],
                          end=form.cleaned_data['end'],
                          purpose=form.cleaned_data['purpose'],
                          installer=form.cleaned_data['installer'],
                          scenario=form.cleaned_data['scenario'],
                          resource=self.resource,
                          owner=user
                          )
        try:
            booking.save()
        except ValueError as err:
            messages.add_message(self.request, messages.ERROR, err)
            return super(BookingFormView, self).form_invalid(form)
        messages.add_message(self.request, messages.SUCCESS, 'Booking saved')
        return super(BookingFormView, self).form_valid(form)


class BookingEditFormView(FormView):
    template_name = "booking/booking_calendar.html"
    form_class = BookingEditForm

    def is_valid(self):
        return True

    def dispatch(self, request, *args, **kwargs):
        self.resource = get_object_or_404(ResourceBundle, id=self.kwargs['resource_id'])
        self.original_booking = get_object_or_404(Booking, id=self.kwargs['booking_id'])
        return super(BookingEditFormView, self).dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        title = 'Editing Booking on: ' + self.resource.name
        context = super(BookingEditFormView, self).get_context_data(**kwargs)
        context.update({'title': title, 'resource': self.resource, 'booking': self.original_booking})

        drop_filter(context)

        return context

    def get_form_kwargs(self):
        kwargs = super(BookingEditFormView, self).get_form_kwargs()
        kwargs['purpose'] = self.original_booking.purpose
        kwargs['start'] = self.original_booking.start
        kwargs['end'] = self.original_booking.end
        return kwargs

    def get_success_url(self):
        return reverse('booking:create', args=(self.resource.id,))

    def form_valid(self, form):

        if not self.request.user.is_authenticated:
            messages.add_message(self.request, messages.ERROR,
                                 'You need to be logged in to book a Pod.')
            return super(BookingEditFormView, self).form_invalid(form)

        if not self.request.user == self.original_booking.user:
            messages.add_message(self.request, messages.ERROR,
                                 'You are not the owner of this booking.')
            return super(BookingEditFormView, self).form_invalid(form)

        # Do Conflict Checks
        if self.original_booking.end != form.cleaned_data['end']:
            if form.cleaned_data['end'] - self.original_booking.end > timezone.timedelta(days=7):
                messages.add_message(self.request, messages.ERROR,
                                     'Extensions can not be longer than one week.')
                return super(BookingEditFormView, self).form_invalid(form)
            elif self.original_booking.ext_count <= 0:
                messages.add_message(self.request, messages.ERROR,
                                     'Cannot change end date after maximum number of extensions reached.')
                return super(BookingEditFormView, self).form_invalid(form)

            else:
                self.original_booking.ext_count -= 1

        if self.original_booking.start != form.cleaned_data['start']:
            if timezone.now() > form.cleaned_data['start']:
                messages.add_message(self.request, messages.ERROR,
                                     'Cannot change start date after it has occurred.')
                return super(BookingEditFormView, self).form_invalid(form)
        self.original_booking.start = form.cleaned_data['start']
        self.original_booking.end = form.cleaned_data['end']
        self.original_booking.purpose = form.cleaned_data['purpose']
        self.original_booking.installer = form.cleaned_data['installer']
        self.original_booking.scenario = form.cleaned_data['scenario']
        self.original_booking.reset = form.cleaned_data['reset']
        try:
            self.original_booking.save()
        except ValueError as err:
            messages.add_message(self.request, messages.ERROR, err)
            return super(BookingEditFormView, self).form_invalid(form)

        return super(BookingEditFormView, self).form_valid(form)


class BookingView(TemplateView):
    template_name = "booking/booking_detail.html"

    def get_context_data(self, **kwargs):
        booking = get_object_or_404(Booking, id=self.kwargs['booking_id'])
        title = 'Booking Details'
        context = super(BookingView, self).get_context_data(**kwargs)
        context.update({'title': title, 'booking': booking})
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


class ResourceBookingsJSON(View):
    def get(self, request, *args, **kwargs):
        resource = get_object_or_404(ResourceBundle, id=self.kwargs['resource_id'])
        bookings = resource.booking_set.get_queryset().values(
            'id',
            'start',
            'end',
            'purpose',
            'jira_issue_status',
            'config_bundle__name'
        )
        return JsonResponse({'bookings': list(bookings)})


def booking_detail_view(request, booking_id):
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

    booking = get_object_or_404(Booking, id=booking_id)
    return render(request, "booking/booking_detail.html", {
        'title': 'Booking Details',
        'booking': booking,
        'pdf': ResourceManager().makePDF(booking.resource),
        'user_id': user.id})


def booking_stats_view(request):
    return render(
            request,
            "booking/stats.html",
            context={
                "data": StatisticsManager.getContinuousBookingTimeSeries(),
                "title": "Booking Statistics"
                }
            )


def booking_stats_json(request):
    try:
        span = int(request.GET.get("days", 14))
    except:
        span = 14
    return JsonResponse(StatisticsManager.getContinuousBookingTimeSeries(span), safe=False)
