##############################################################################
# Copyright (c) 2018 Sawyer Bergeron and others.
#
# All rights reserved. This program and the accompanying materials
# are made available under the terms of the Apache License, Version 2.0
# which accompanies this distribution, and is available at
# http://www.apache.org/licenses/LICENSE-2.0
##############################################################################

from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0003_auto_20180108_2024'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='ext_count',
            field=models.IntegerField(default=2),
        ),
    ]
