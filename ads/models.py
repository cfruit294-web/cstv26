from django.db import models

from core.models import BaseModel


def ad_video_upload_path(instance, filename):
    return f'ads/videos/{instance.id}/{filename}'


def ad_image_upload_path(instance, filename):
    return f'ads/images/{instance.id}/{filename}'


class Ad(BaseModel):
    """Publicité gérée par l'admin, diffusée à un emplacement donné (pre-roll pour l'instant)."""

    class CreativeType(models.TextChoices):
        VIDEO = 'video', 'Vidéo'
        IMAGE = 'image', 'Image'

    class Placement(models.TextChoices):
        PRE_ROLL = 'pre_roll', 'Avant la vidéo'

    title = models.CharField(max_length=255)
    creative_type = models.CharField(max_length=10, choices=CreativeType.choices)
    placement = models.CharField(max_length=20, choices=Placement.choices, default=Placement.PRE_ROLL)

    video_file = models.FileField(upload_to=ad_video_upload_path, blank=True, null=True)
    image = models.ImageField(upload_to=ad_image_upload_path, blank=True, null=True)
    # Utilisé pour l'affichage des images (durée du palier) et, si renseigné, comme minuteur pour les
    # vidéos ; laissé vide pour une vidéo, le lecteur se contente de l'évènement natif de fin de lecture.
    duration_seconds = models.PositiveIntegerField(blank=True, null=True)

    click_url = models.URLField(blank=True, help_text='Lien "En savoir plus" (optionnel).')
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.creative_type == self.CreativeType.VIDEO and not self.video_file:
            raise ValidationError("Une publicité vidéo doit avoir un fichier vidéo.")
        if self.creative_type == self.CreativeType.IMAGE and not self.image:
            raise ValidationError("Une publicité image doit avoir une image.")
        if self.creative_type == self.CreativeType.IMAGE and not self.duration_seconds:
            raise ValidationError("Une publicité image doit avoir une durée d'affichage.")
