from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_order_orderitem"),
    ]

    operations = [
        migrations.AddField(
            model_name="category",
            name="name_en",
            field=models.CharField(
                blank=True,
                default="",
                max_length=200,
                verbose_name="Назва категорії (англійською)",
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="title_en",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Назва (англійською)",
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="author_en",
            field=models.CharField(
                blank=True,
                default="",
                max_length=255,
                verbose_name="Автор (англійською)",
            ),
        ),
        migrations.AddField(
            model_name="book",
            name="description_en",
            field=models.TextField(
                blank=True,
                default="",
                verbose_name="Опис (англійською)",
            ),
        ),
    ]
