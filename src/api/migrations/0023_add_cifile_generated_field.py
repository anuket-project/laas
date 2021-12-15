from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('api', '0022_merge_20211102_2136'),
    ]

    operations = [
        migrations.AddField(
            model_name="CloudInitFile",
            name="generated",
            field=models.BooleanField(default=False)
        ),
    ]
