##############################################################################
# Copyright (c) 2018 Parker Berberian, Sawyer Bergeron, and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################
from django.test import TestCase
from django.contrib.auth.models import User
from account.models import Lab
from resource_inventory.models import *


class ConfigUtil():
    count=0

    @staticmethod
    def makeScenario():
        return Scenario.objects.create(name="testScenario")

    @staticmethod
    def makeInstaller():
        inst = Installer.objects.create(
            name = "testInstaller"
        )
        inst.sup_scenarios = [ConfigUtil.makeScenario()]
        return inst

    @staticmethod
    def makeOpsys():
        os = Opsys.objects.create(
            name = "test Operating System"
        )
        os.sup_installers = [ConfigUtil.makeInstaller()]
        return os

    @staticmethod
    def makeConfigBundle():
        user = User.objects.create(username="test_user" + str(ConfigUtil.count))
        ConfigUtil.count += 1
        return ConfigBundle.objects.create(
            owner = user
        )

    @staticmethod
    def makeOPNFVConfig():
        installer = ConfigUtil.makeInstaller()
        scenario = ConfigUtil.makeScenario()
        bundle = ConfigUtil.makeConfigBundle()
        return OPNFVConfig.objects.create(
                installer=installer,
                scenario=scenario,
                bundle=bundle
                )

    @staticmethod
    def makeOPNFVRole():
        return OPNFVRole.objects.create(
                name="Test role",
                description="This is a test role"
                )

    @staticmethod
    def makeImage():
        owner = User.objects.create(username="another test user")
        lab_user = User.objects.create(username="labUserForTests")
        lab = Lab.objects.create(
                lab_user=lab_user,
                name="this is lab for testing",
                contact_email="email@mail.com",
                contact_phone="123-4567"
                )

        return Image.objects.create(
                lab_id=0,
                from_lab=lab,
                name="an image for testing",
                owner=owner
                )


    @staticmethod
    def makeGenericHost():
        profile = HostProfile.objects.create(
                host_type=0,
                name="test lab for config bundle",
                description="this is a test profile"
                )
        user = User.objects.create(username="test sample user 12")
        bundle = GenericResourceBundle.objects.create(
                name="Generic bundle for config tests",
                xml="",
                owner=user,
                description=""
                )

        resource = GenericResource.objects.create(
                bundle=bundle,
                name="a test generic resource"
                )

        return GenericHost.objects.create(
                profile=profile,
                resource=resource
                )

    @staticmethod
    def makeHostConfiguration():
        host = ConfigUtil.makeGenericHost()
        image = ConfigUtil.makeImage()
        bundle = ConfigUtil.makeConfigBundle()
        opnfvRole = ConfigUtil.makeOPNFVRole()
        return HostConfiguration.objects.create(
                host=host,
                image=image,
                bundle=bundle,
                opnfvRole=opnfvRole
                )


class ScenarioTestCase(TestCase):

    def test_save(self):
        self.assertTrue(ConfigUtil.makeScenario())

class InstallerTestCase(TestCase):

    def test_save(self):
        self.assertTrue(ConfigUtil.makeInstaller())

class OperatingSystemTestCase(TestCase):

    def test_save(self):
        self.assertTrue(ConfigUtil.makeOpsys())

class ConfigBundleTestCase(TestCase):

    def test_save(self):
        self.assertTrue(ConfigUtil.makeConfigBundle())

class OPNFVConfigTestCase(TestCase):

    def test_save(self):
        self.assertTrue(ConfigUtil.makeOPNFVConfig())

class OPNFVRoleTestCase(TestCase):

    def test_save(self):
        self.assertTrue(ConfigUtil.makeOPNFVRole())


class HostConfigurationTestCase(TestCase):

    def test_save(self):
        self.assertTrue(ConfigUtil.makeHostConfiguration())


class ImageTestCase(TestCase):

    def test_save(self):
        self.assertTrue(ConfigUtil.makeImage())
