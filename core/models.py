import uuid

from django.db import models


class UUIDModel(models.Model):
    """Modèle abstrait utilisant un UUID comme clé primaire."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    class Meta:
        abstract = True


class TimeStampedModel(models.Model):
    """Modèle abstrait ajoutant les horodatages de création/mise à jour."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class SoftDeleteQuerySet(models.QuerySet):
    def alive(self):
        return self.filter(deleted_at__isnull=True)

    def dead(self):
        return self.filter(deleted_at__isnull=False)


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return SoftDeleteQuerySet(self.model, using=self._db).alive()


class SoftDeleteModel(models.Model):
    """Modèle abstrait implémentant la suppression logique (soft delete)."""

    deleted_at = models.DateTimeField(null=True, blank=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()

    class Meta:
        abstract = True

    def delete(self, using=None, keep_parents=False):
        from django.utils import timezone

        self.deleted_at = timezone.now()
        self.save(using=using, update_fields=['deleted_at'])

    def hard_delete(self, using=None, keep_parents=False):
        super().delete(using=using, keep_parents=keep_parents)

    @property
    def is_deleted(self):
        return self.deleted_at is not None


class BaseModel(UUIDModel, TimeStampedModel):
    """Socle commun (UUID + horodatages) pour les modèles métier de la plateforme."""

    class Meta:
        abstract = True
