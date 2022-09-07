from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('api', '0018_cloudinitfile'),
    ]

    operations = [
        migrations.AddField(
            model_name="CloudInitFile",
            name="generated",
            field=models.BooleanField(default=False)
        ),
    ]
