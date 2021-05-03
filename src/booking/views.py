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

from resource_inventory.models import ResourceBundle, ResourceProfile, Image, ResourceQuery
from account.models import Downtime, Lab
from booking.models import Booking
from booking.stats import StatisticsManager
from booking.forms import HostReImageForm
from workflow.forms import FormUtils
from api.models import JobFactory
from workflow.views import login
from booking.forms import QuickBookingForm
from booking.quick_deployer import create_from_form, drop_filter


def quick_create_clear_fields(request):
    request.session['quick_create_forminfo'] = None


def quick_create(request):
    if not request.user.is_authenticated:
        return login(request)

    if request.method == 'GET':
        context = {}
        attrs = FormUtils.getLabData(user=request.user)
        context['form'] = QuickBookingForm(lab_data=attrs, default_user=request.user.username, user=request.user)
        context['lab_profile_map'] = {}
        context.update(drop_filter(request.user))
        context['contact_email'] = Lab.objects.filter(name="UNH_IOL").first().contact_email
        return render(request, 'booking/quick_deploy.html', context)

    if request.method == 'POST':
        attrs = FormUtils.getLabData(user=request.user)
        form = QuickBookingForm(request.POST, lab_data=attrs, user=request.user)

        context = {}
        context['lab_profile_map'] = {}
        context['form'] = form

        if form.is_valid():
            try:
                booking = create_from_form(form, request)
                messages.success(request, "We've processed your request. "
                                          "Check Account->My Bookings for the status of your new booking")
                return redirect(reverse('booking:booking_detail', kwargs={'booking_id': booking.id}))
            except Exception as e:
                messages.error(request, "Whoops, an error occurred: " + str(e))
                context.update(drop_filter(request.user))
                return render(request, 'booking/quick_deploy.html', context)
        else:
            messages.error(request, "Looks like the form didn't validate. Check that you entered everything correctly")
            context['status'] = 'false'
            context.update(drop_filter(request.user))
            return render(request, 'booking/quick_deploy.html', context)


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


def build_image_mapping(lab, user):
    mapping = {}
    for profile in ResourceProfile.objects.filter(labs=lab):
        images = Image.objects.filter(
            from_lab=lab,
            host_type=profile
        ).filter(
            Q(public=True) | Q(owner=user)
        )
        mapping[profile.name] = [{"name": image.name, "value": image.id} for image in images]
    return mapping


def booking_detail_view(request, booking_id):
    user = None
    if request.user.is_authenticated:
        user = request.user
    else:
        return render(request, "dashboard/login.html", {'title': 'Authentication Required'})

    booking = get_object_or_404(Booking, id=booking_id)
    allowed_users = set(list(booking.collaborators.all()))
    allowed_users.add(booking.owner)
    if user not in allowed_users:
        return render(request, "dashboard/login.html", {'title': 'This page is private'})

    context = {
        'title': 'Booking Details',
        'booking': booking,
        'pdf': booking.pdf,
        'user_id': user.id,
        'image_mapping': build_image_mapping(booking.lab, user)
    }

    return render(
        request,
        "booking/booking_detail.html",
        context
    )


def booking_modify_image(request, booking_id):
    form = HostReImageForm(request.POST)
    if form.is_valid():
        booking = Booking.objects.get(id=booking_id)
        if request.user != booking.owner:
            return HttpResponse("unauthorized")
        if timezone.now() > booking.end:
            return HttpResponse("unauthorized")
        new_image = Image.objects.get(id=form.cleaned_data['image_id'])
        host = ResourceQuery.get(id=form.cleaned_data['host_id'])
        host.config.image = new_image
        host.config.save()
        JobFactory.reimageHost(new_image, booking, host)
        return HttpResponse(new_image.name)
    return HttpResponse("error")


def booking_stats_view(request):
    return render(
        request,
        "booking/stats.html",
        context={"data": StatisticsManager.getContinuousBookingTimeSeries(), "title": ""}
    )


def booking_stats_json(request):
    try:
        span = int(request.GET.get("days", 14))
    except Exception:
        span = 14
    return JsonResponse(StatisticsManager.getContinuousBookingTimeSeries(span), safe=False)
