from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="SafetyEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_type", models.CharField(choices=[("danger","Danger"),("safe","Safe"),("belt_moving","Belt Moving"),("belt_stationary","Belt Stationary")], default="safe", max_length=20)),
                ("belt_status", models.CharField(choices=[("moving","Moving"),("stationary","Stationary"),("unknown","Unknown")], default="unknown", max_length=20)),
                ("person_detected", models.BooleanField(default=False)),
                ("danger", models.BooleanField(default=False)),
                ("email_sent", models.BooleanField(default=False)),
                ("screenshot", models.ImageField(blank=True, null=True, upload_to="screenshots/")),
                ("timestamp", models.DateTimeField(auto_now_add=True)),
                ("notes", models.TextField(blank=True, null=True)),
            ],
            options={"db_table": "safety_events", "ordering": ["-timestamp"]},
        ),
    ]
