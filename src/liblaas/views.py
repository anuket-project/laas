##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

# Unauthenticated requests to liblaas. If a call makes it to here, it is assumed to be authenticated

import os
import requests
import json

base = os.environ.get("LIBLAAS_BASE_URL")
post_headers = {'Content-Type': 'application/json'}

def liblaas_docs():
    endpoint = f'docs'
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

### BOOKING

# DELETE
def booking_end_booking(agg_id: str) -> requests.Response:
    endpoint = f'booking/{agg_id}/end'
    url = f'{base}{endpoint}'
    try:
        response = requests.delete(url)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

# GET
def booking_booking_status(agg_id: str) -> requests.Response:
    endpoint = f'booking/{agg_id}/status'
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

# POST
def booking_create_booking(booking_blob: dict) -> requests.Response:
    endpoint = f'booking/create'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(booking_blob), headers=post_headers)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

### FLAVOR

# GET
def flavor_list_flavors(project: str) -> requests.Response:
    endpoint = f'flavor' #todo - add project to url once liblaas supports it
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

# GET
def flavor_list_hosts(project: str) -> requests.Response:
    endpoint = f'flavor/hosts/{project}' #todo - support project in liblaas
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

### TEMPLATE

# GET
def template_list_templates(uid: str) -> requests.Response:
    endpoint = f'template/list/{uid}' # todo - templates need to be restricted by project
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

# DELETE
def template_delete_template(template_id: str) -> requests.Response:
    endpoint = f'template/{template_id}'
    url = f'{base}{endpoint}'
    try:
        response = requests.delete(url)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

#POST
def template_make_template(template_blob: dict) -> requests.Response:
    endpoint = f'template/create' # todo - needs to be restricted by project
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(template_blob), headers=post_headers)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

### USER

# GET
def user_get_user(uid: str) -> requests.Response:
    endpoint = f'user/{uid}'
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except:
        print(f"Error at {url}")
        return None

# POST
def user_create_user(user_blob: dict) -> requests.Response:
    endpoint = f'user/create'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(user_blob), headers=post_headers)
        # LibLaaS is not returning anything here regardless, so we need some way of determining if it was successful
        # return response.json()

        if response.status_code == 200:
            return user_blob["uid"]
        
        return response.json()
    except:
        print(f"Error at {url}")
        return None

# POST
def user_set_ssh(uid: str, keys: list) -> requests.Response:
    endpoint = f'user/{uid}/ssh'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(clean_ssh_keys(keys)), headers=post_headers)
        # return response.json()
        return response.status_code == 200
    except:
        print(f"Error at {url}")
        return None

# POST
def user_set_company(uid: str, company: str):
    endpoint = f'user/{uid}/company'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(company), headers=post_headers)
        # return response.json()
        return response.status_code == 200
    except:
        print(f"Error at {url}")
        return None

# POST
def user_set_email(uid: str, email: str):
    endpoint = f'user/{uid}/email'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(email), headers=post_headers)
        # return response.json()
        return response.status_code == 200
    except:
        print(f"Error at {url}")
        return None

# utils
def clean_ssh_keys(ssh_key_list):
    cleaned = []
    for key in ssh_key_list:
        cleaned.append(key.strip())
    return cleaned