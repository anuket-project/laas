##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

# Unauthenticated requests to liblaas. If a call makes it to here, it is assumed to be authenticated
# Responses that return json will return the unwrapped json data, otherwise it will return whether the request was successful or not

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
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

### BOOKING

# DELETE
def booking_end_booking(agg_id: str) -> bool:
    endpoint = f'booking/{agg_id}/end'
    url = f'{base}{endpoint}'
    try:
        response = requests.delete(url)
        return True # liblaas actually doesn't return an HTTP response here for some reason
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

# GET
def booking_booking_status(agg_id: str) -> dict:
    endpoint = f'booking/{agg_id}/status'
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

# POST
def booking_create_booking(booking_blob: dict) -> str:
    endpoint = f'booking/create'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(booking_blob), headers=post_headers)
        return response.json()
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

### FLAVOR

# GET
def flavor_list_flavors(project: str) -> list[dict]:
    endpoint = f'flavor' #todo - add project to url once liblaas supports it
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

# GET
def flavor_list_hosts(project: str) -> list[dict]:
    endpoint = f'flavor/hosts/{project}' #todo - support project in liblaas
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

### TEMPLATE

# GET
def template_list_templates(uid: str) -> list[dict]:
    endpoint = f'template/list/{uid}' # todo - templates need to be restricted by project
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

# DELETE
def template_delete_template(template_id: str) -> bool:
    endpoint = f'template/{template_id}'
    url = f'{base}{endpoint}'
    try:
        response = requests.delete(url)
        return response.status_code == 200

    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

#POST
def template_make_template(template_blob: dict) -> str:
    endpoint = f'template/create' # todo - needs to be restricted by project
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(template_blob), headers=post_headers)
        return response.json()
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

### USER

# GET
def user_get_user(uid: str) -> dict:
    endpoint = f'user/{uid}'
    url = f'{base}{endpoint}'
    try:
        response = requests.get(url)
        return response.json()
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

# POST
def user_create_user(user_blob: dict) -> bool:
    endpoint = f'user/create'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(user_blob), headers=post_headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

# POST
def user_set_ssh(uid: str, keys: list) -> bool:
    endpoint = f'user/{uid}/ssh'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(clean_ssh_keys(keys)), headers=post_headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

# POST
def user_set_company(uid: str, company: str) -> bool:
    endpoint = f'user/{uid}/company'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(company), headers=post_headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

# POST
def user_set_email(uid: str, email: str) -> bool:
    endpoint = f'user/{uid}/email'
    url = f'{base}{endpoint}'
    try:
        response = requests.post(url, data=json.dumps(email), headers=post_headers)
        return response.status_code == 200
    except Exception as e:
        print(f"Error at {url}")
        print(e)
        return None

# utils
def clean_ssh_keys(ssh_key_list: list[str]) -> list[str]:
    cleaned = []
    for key in ssh_key_list:
        cleaned.append(key.strip())
    return cleaned