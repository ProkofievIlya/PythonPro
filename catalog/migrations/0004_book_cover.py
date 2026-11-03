from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0003_english_translations"),
    ]

    operations = [
        migrations.AddField(
            model_name="book",
            name="cover",
            field=models.ImageField(blank=True, upload_to="covers/", verbose_name="Обкладинка"),
        ),
    ]
