##############################################################################
# Copyright (c) 2020 Sean Smith and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from django.db import models
from account.models import Lab


class ActiveVPNUser(models.Model):
    """ Keeps track of how many VPN Users are connected to Lab """
    time_stamp = models.DateTimeField(auto_now_add=True)
    lab = models.ForeignKey(Lab, on_delete=models.CASCADE, null=False)
    active_users = models.IntegerField()

    @classmethod
    def create(cls, lab_name, active_users):
        """
        This creates an Active VPN Users entry from
        from lab_name as a string
        """

        lab = Lab.objects.get(name=lab_name)
        avu = cls(lab=lab, active_users=active_users)
        avu.save()
        return avu
