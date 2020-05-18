##############################################################################
# Copyright (c) 2020 Sawyer Bergeron, Parker Berberian, Sean Smith, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################


from resource_inventory.models import (
    ResourceProfile,
    ResourceQuery,
    Image,
    DiskProfile,
    CpuProfile,
    RamProfile,
    InterfaceProfile,
)


def rp_has_all_components():
    """
    Check that every ResourceProfile has an InterfaceProfile,
    DiskProfile, CpuProfile, and RamProfile.
    """

    result = True

    for rp in ResourceProfile.objects.all():
        ip = InterfaceProfile.objects.filter(host=rp).exists()
        dp = DiskProfile.objects.filter(host=rp).exists()
        cp = CpuProfile.objects.filter(host=rp).exists()
        ram = RamProfile.objects.filter(host=rp).exists()

        if not ip:
            print("No InterfaceProfiles for host", rp.name)
            result = False

        if not dp:
            print("No DiskProfile for host", rp.name)
            result = False

        if not cp:
            print("No CpuProfile for host", rp.name)
            result = False

        if not ram:
            print("No RamProfile for host", rp.name)
            result = False

    return result


def ip_for_all_ifaces():
    """
    Check that every InterfaceProfile for a Resource has
    an Interface.
    """

    result = True

    for res in ResourceQuery.filter():
        iface_set = res.get_interfaces()
        iface_profile_set = InterfaceProfile.objects.filter(host=res.profile)

        # find out what profiles we have
        curr_profiles = [iface.profile for iface in iface_set]
        missing_profiles = set(iface_profile_set) - set(curr_profiles)

        if missing_profiles:
            print('No interface for profiles', missing_profiles, 'for host', res.name)
            result = False

    return result


def rp_has_image():
    """
    Make sure every ResourceProfile has an Image.
    """

    result = True

    rp_set = ResourceProfile.objects.all()
    image_set = Image.objects.all()
    image_profiles = set([image.host_type for image in image_set])

    for rp in rp_set:
        if rp not in image_profiles:
            print("ResourceProfile", rp.name, "has no image associated with it.")
            result = False
    return result


def run_test(test):
    print('RUNNING TEST', test)
    result = test()
    if result:
        print(test, 'WAS A SUCCESS!')
    else:
        print(test, 'FAILED')
    print('============================================')


def run_tests():
    tests = [rp_has_all_components, ip_for_all_ifaces, rp_has_image]

    for test in tests:
        run_test(test)
