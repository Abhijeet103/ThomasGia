from django.db import migrations


def hide_database_google_social_apps(apps, schema_editor):
    SocialApp = apps.get_model("socialaccount", "SocialApp")
    for social_app in SocialApp.objects.filter(provider="google"):
        app_settings = dict(social_app.settings or {})
        app_settings["hidden"] = True
        social_app.settings = app_settings
        social_app.save(update_fields=["settings"])


def restore_database_google_social_apps(apps, schema_editor):
    SocialApp = apps.get_model("socialaccount", "SocialApp")
    for social_app in SocialApp.objects.filter(provider="google"):
        app_settings = dict(social_app.settings or {})
        app_settings.pop("hidden", None)
        social_app.settings = app_settings
        social_app.save(update_fields=["settings"])


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0005_seed_default_site"),
        ("socialaccount", "0006_alter_socialaccount_extra_data"),
    ]

    operations = [
        migrations.RunPython(
            hide_database_google_social_apps,
            restore_database_google_social_apps,
        ),
    ]
