##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.contrib.auth.models import User
from account.models import UserProfile
from liblaas.views import user_get_user, user_get_many_users

def isValidCollaborator(profile: UserProfile) -> bool:
    """
    Fetches the related user from LibLaaS (and IPA subsequently) then returns whether the user has required fields.
    Current required fields are ["ipasshpublickey"]
    """

    if not profile:
        print("UserProfile was None!")
        return False

    ipa_username = profile.ipa_username

    if not ipa_username:
        print("No ipa username for", profile)
        return False
    
    ipa_account = user_get_user(ipa_username)

    if not ipa_account:
        print("Failed to retreieve user for", profile)
        return False

    if not "ipasshpubkey" in ipa_account:
        print("No SSH key for", profile)
        return False

    print("Valid user", profile)
    return True


def find_invalid_collaborators(profiles: list[UserProfile]) -> list[UserProfile]:
    """
    Verifies that the linked IPA accounts of the given userprofiles are valid collaborators.
    See isValidCollaborator() to see what determines if a collaborator is valid or now.

    Assumes ipa_username is set for all provided collaborators
    """
    accounts: list[dict] = user_get_many_users([p.ipa_username for p in profiles])
    failed = []
    for a in accounts:
        if not "ipasshpubkey" in a:
            failed.append(a["uid"])

    return failed

# Returns whether the user has linked their ipa account. If not, determines how it needs to be linked.
def get_ipa_status(dashboard_user: User) -> str:
    profile = UserProfile.objects.get(user=dashboard_user)
    if profile == None:
        return "n/a"

    # Already linked, no need to continue
    if profile.ipa_username != None:
        return "n/a"
    
    # Basic info
    dashboard_username = str(dashboard_user)
    dashboard_email = profile.email_addr
    ipa_user = user_get_user(dashboard_username)

    # New user case
    if ipa_user == None:
        return "new"

    # Link case
    if ipa_user["mail"] == dashboard_email:
        return "link"

    # Conflict case
    return "conflict"
