##############################################################################
# Copyright (c) 2019 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from account.models import UserProfile


def get_user_field_opts():
    return {
        'show_from_noentry': False,
        'show_x_results': 5,
        'results_scrollable': True,
        'selectable_limit': -1,
        'placeholder': 'Search for other users',
        'name': 'users',
        'disabled': False
    }


def get_user_items(exclude=None):
    qs = UserProfile.objects.select_related('user').exclude(user=exclude)
    items = {}
    for up in qs:
        item = {
            'id': up.id,
            'expanded_name': up.full_name,
            'small_name': up.user.username,
            'string': up.email_addr
        }
        items[up.id] = item
    return items
