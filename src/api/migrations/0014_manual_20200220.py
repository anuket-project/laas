
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0013_manual_20200218_1536'),
        ('resource_inventory', '0013_auto_20200218_1536')
    ]

    operations = [
        migrations.AddField(
            model_name='opnfvapiconfig',
            name='roles',
            field=models.ManyToManyField(to='resource_inventory.ResourceOPNFVConfig'),
        ),
    ]
