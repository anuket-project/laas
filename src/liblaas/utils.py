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
from liblaas.views import user_get_user

def validate_collaborators(collab_list: list[str]) -> dict:
    result = {"message": "n/a", "valid": False}

    for user in collab_list:
        collab_profile = UserProfile.objects.get(user=User.objects.get(username=user))
        ipa_username = collab_profile.ipa_username
        if ipa_username == None:
            result["message"] = f"{str(collab_profile)} has not linked their IPA account yet. Please ask them to log into the LaaS dashboard, or remove them from the booking to continue."
            return result

        ipa_account = user_get_user(ipa_username)
        print(ipa_account)

        if not "ou" in ipa_account or ipa_account["ou"] == "":
            result["message"] = f"{str(collab_profile)} has not set their company yet. Please ask them to log into the LaaS dashboard, go to the settings page and add it. Otherwise, remove them from the booking to continue."
            return result

        if not "ipasshpubkey" in ipa_account:
            result["message"] = f"{str(collab_profile)} has not added an SSH public key yet. Please ask them to log into the LaaS dashboard, go to the settings page and add it. Otherwise, remove them from the booking to continue."
            return result

    result["valid"] = True

    return result

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
