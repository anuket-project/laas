/*****************************************************************************
 * Copyright (c) 2016 Max Breitenfeldt and others.
 *
 * All rights reserved. This program and the accompanying materials
 * are made available under the terms of the Apache License, Version 2.0
 * which accompanies this distribution, and is available at
 * http://www.apache.org/licenses/LICENSE-2.0
 *****************************************************************************/


function parseCalendarEvents(bookings) {
    var events = [];
    for (var i = 0; i < bookings.length; i++) {
        // convert ISO 8601 timestring to moment, needed for timezone handling
        start = moment(bookings[i]['start']);
        end = moment(bookings[i]['end']);

        installer = bookings[i]['installer__name'];
        if (installer === null) {
            installer = '';
        }

        scenario = bookings[i]['scenario__name'];
        if (scenario === null) {
            scenario = '';
        }
        title = bookings[i]['purpose'] + ' ' + installer + ' ' + scenario;

        event = {
            id: bookings[i]['id'],
            title: title,
            start: start,
            end: end,
        };
        events.push(event);
    }
    return events;
}

function loadEvents(url) {
    $.ajax({
        url: url,
        type: 'get',
        success: function (data) {
            $('#calendar').fullCalendar('addEventSource', parseCalendarEvents(data['bookings']));
        },
        failure: function (data) {
            alert('Error loading booking data');
        }
    });
}

$(document).ready(function () {
    createEditViewSwitch();
    $('#calendar').fullCalendar(calendarOptions);
    loadEvents(bookings_url);
    $('#starttimepicker').datetimepicker(timepickerOptions);
    $('#endtimepicker').datetimepicker(timepickerOptions);
    $('#starttimeeditpicker').datetimepicker(timepickerOptions);
    $('#endtimeeditpicker').datetimepicker(timepickerOptions);
});

function createEditViewSwitch() {
    var url = window.location.href;
    var isEdit = url.substr(url.lastIndexOf('/'));

    if ( url.indexOf('edit') !== -1 ) {
        document.getElementById('booking_form_div').style.display = 'none';
        calendarOptions.selectable = false;
    } else {
        document.getElementById('booking_edit_form_div').style.display = 'none';
    }
}
