import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0001_initial"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Order",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("email", models.EmailField(max_length=254, verbose_name="Email")),
                ("status", models.CharField(choices=[("pending", "Очікує оплату"), ("paid", "Оплачено"), ("cancelled", "Скасовано")], default="pending", max_length=20, verbose_name="Статус")),
                ("total", models.DecimalField(decimal_places=2, default=0, max_digits=10, verbose_name="Сума")),
                ("stripe_session_id", models.CharField(blank=True, max_length=255, null=True, unique=True, verbose_name="Stripe session")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="orders", to=settings.AUTH_USER_MODEL, verbose_name="Користувач")),
            ],
            options={
                "verbose_name": "Замовлення",
                "verbose_name_plural": "Замовлення",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="OrderItem",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("price", models.DecimalField(decimal_places=2, max_digits=10, verbose_name="Ціна")),
                ("quantity", models.PositiveIntegerField(default=1, verbose_name="Кількість")),
                ("book", models.ForeignKey(on_delete=django.db.models.deletion.PROTECT, related_name="order_items", to="catalog.book", verbose_name="Книга")),
                ("order", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="items", to="catalog.order", verbose_name="Замовлення")),
            ],
            options={
                "verbose_name": "Позиція замовлення",
                "verbose_name_plural": "Позиції замовлення",
            },
        ),
    ]
