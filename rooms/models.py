from django.db import models
from django.urls import reverse
from django.utils.text import slugify


class Equipment(models.Model):
    name = models.CharField("Название", max_length=120, unique=True)
    slug = models.SlugField("Slug", max_length=140, unique=True, blank=True)
    description = models.TextField("Описание", blank=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Оснащение"
        verbose_name_plural = "Оснащение"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class MeetingRoom(models.Model):
    class ApprovalPolicy(models.TextChoices):
        AUTOMATIC = "automatic", "Автоматическое подтверждение"
        MANUAL = "manual", "Ручное согласование"

    name = models.CharField("Название", max_length=120)
    slug = models.SlugField("Slug", max_length=140, unique=True, blank=True)
    location = models.CharField("Локация", max_length=140)
    floor = models.PositiveIntegerField("Этаж")
    capacity = models.PositiveIntegerField("Вместимость")
    description = models.TextField("Описание")
    equipment = models.ManyToManyField(Equipment, verbose_name="Оснащение", blank=True, related_name="rooms")
    approval_policy = models.CharField(
        "Политика подтверждения",
        max_length=16,
        choices=ApprovalPolicy.choices,
        default=ApprovalPolicy.AUTOMATIC,
    )
    is_active = models.BooleanField("Доступна для бронирования", default=True)
    created_at = models.DateTimeField("Создана", auto_now_add=True)
    updated_at = models.DateTimeField("Обновлена", auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Переговорная"
        verbose_name_plural = "Переговорные"

    def __str__(self) -> str:
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("rooms:detail", kwargs={"slug": self.slug})

    @property
    def requires_moderation(self) -> bool:
        return self.approval_policy == self.ApprovalPolicy.MANUAL

