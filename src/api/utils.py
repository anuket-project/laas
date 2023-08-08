# These functions are called from views and perform the actual request to LibLaaS

import json
from django.http.response import JsonResponse, HttpResponse
import requests
import os

from dashboard.forms import *
liblaas_base_url = os.environ.get("LIBLAAS_BASE_URL")

# IPA Stuff
def ipa_query_user(ipa_username):
    url = liblaas_base_url + "user/" + ipa_username
    print("Getting ipa user for", ipa_username, url)
    try:
        response = requests.get(url)
        data = response.json()
        print("ipa user is", data)
        return data # Expects a dict
    except Exception as e:
        print(e)
        return None
    
# Queries for an IPA user using dashboard username
# Returns a result
def get_ipa_migration_form(user, profile):
    # ipa_user = ipa_query_user(str(dashboard_user))
    # if (ipa_user and ipa_user.mail is )
    # pass
    dashboard_username = str(user)
    dashboard_email = profile.email_addr
    first_name = user.first_name
    last_name = user.last_name

    ipa_user = ipa_query_user(dashboard_username)
    print("Attempting auto migration with", dashboard_username, dashboard_email, ipa_user)
    if (ipa_user):
        if (dashboard_email == ipa_user["mail"]):
        # User is found and email match
            print("User is found and email match")
            return {
                "form": ReadOnlyIPAAccountForm(initial={'ipa_username': ipa_user['uid'],'first_name': ipa_user["givenname"], 'last_name': ipa_user["sn"], 'email': ipa_user["mail"], 'company': ipa_user["ou"]}),
                "message": "We have located the following IPA account matching your username and email. Please confirm to link your account. You may change these details at any time.",
                "action": "api/ipa/confirm",
                "button": "Link"
            }

        else:
        # User is found and emails don't match
            print("User is found and emails don't match")
            return {
                "form": ConflictIPAAcountForm(initial={'first_name': first_name, 'last_name': last_name, 'email': dashboard_email}),
                "message": "Our records indicate that you do not currently have an account in our IPA system, or your emails do not match. Please enter the following details to enroll your account.",
                "action": "/",
                "button": "Submit"
            }
    else:
    # User is not found
        print("User is not found")
        return {
            "form": NewIPAAccountForm(initial={'first_name': first_name, 'last_name': last_name, 'email': dashboard_email}),
            "message": "Our records indicate that you do not currently have an account in our IPA system, or your usernames do not match. Please enter the following details to enroll your account.",
            "action": "api/ipa/create",
            "button": "Submit"
        }

# Take a list of strings, sends it to liblaas, replacing the IPA keys with the new keys
def ipa_set_ssh(user_profile, ssh_key_list):
    url = liblaas_base_url + "user/" + user_profile.ipa_username + "/ssh"
    print(ssh_key_list)
    print("Setting SSH keys with URL", url)
    try:
        requests.post(url, data=json.dumps(ssh_key_list), headers={'Content-Type': 'application/json'})
        return HttpResponse(status=200)
    except Exception as e:
        print(e)
        return HttpResponse(status=500)
    
def ipa_set_company(user_profile, company_name):
    url = liblaas_base_url + "user/" + user_profile.ipa_username + "/company"
    print("Setting company with URL", url)
    try:
        requests.post(url, data=json.dumps(company_name), headers={'Content-Type': 'application/json'})
        return HttpResponse(status=200)
    except Exception as e:
        print(e)
        return HttpResponse(status=500)

def get_booking_prereqs_validator(user_profile):
    ipa_user = None
    if (user_profile.ipa_username != None and user_profile.ipa_username != ""):
        ipa_user = ipa_query_user(user_profile.ipa_username)

    if ipa_user == None:
        print("No user")
        return {
            "form": None,
            "exists": "false",
            "action": "no user",
            "result": 0
        }

    if (not "ou" in ipa_user) or (ipa_user["ou"] == ""):
        print("Missing company")
        return {
            "form": SetCompanyForm(),
            "exists": "true",
            "action": "/api/ipa/workflow-company",
            "result": 1
        }
    
    if (not "ipasshpubkey" in ipa_user) or (ipa_user["ipasshpubkey"] == []):
        print("Missing SSH key")
        return {
            "form": SetSSHForm(),
            "exists": "true",
            "action": "/api/ipa/workflow-ssh",
            "result": 2,
        }

    return {
        "form": None,
        "exists": "false",
        "action": "",
        "result": -1
    }