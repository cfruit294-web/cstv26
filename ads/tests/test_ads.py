from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from ads.models import Ad


def _image_file(name='ad.jpg'):
    # Plus petit PNG valide possible (1x1) : suffisant pour ImageField.
    content = (
        b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00'
        b'\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xcf\xc0\x00\x00\x03\x01\x01\x00\x18\xdd\x8d\xb0'
        b'\x00\x00\x00\x00IEND\xaeB`\x82'
    )
    return SimpleUploadedFile(name, content, content_type='image/png')


class NextAdViewTests(APITestCase):
    def test_no_active_ad_returns_204(self):
        response = self.client.get(reverse('ads:next-ad'))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_returns_active_pre_roll_ad(self):
        ad = Ad.objects.create(
            title='Pub test', creative_type=Ad.CreativeType.IMAGE, placement=Ad.Placement.PRE_ROLL,
            image=_image_file(), duration_seconds=5, is_active=True,
        )
        response = self.client.get(reverse('ads:next-ad'), {'placement': 'pre_roll'})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], str(ad.id))

    def test_ignores_inactive_ads(self):
        Ad.objects.create(
            title='Pub inactive', creative_type=Ad.CreativeType.IMAGE, placement=Ad.Placement.PRE_ROLL,
            image=_image_file(), duration_seconds=5, is_active=False,
        )
        response = self.client.get(reverse('ads:next-ad'))
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_ignores_other_placements(self):
        Ad.objects.create(
            title='Pub mid-roll', creative_type=Ad.CreativeType.IMAGE, placement='mid_roll',
            image=_image_file(), duration_seconds=5, is_active=True,
        )
        response = self.client.get(reverse('ads:next-ad'), {'placement': 'pre_roll'})
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class AdModelValidationTests(APITestCase):
    def test_video_ad_requires_video_file(self):
        ad = Ad(title='Sans fichier', creative_type=Ad.CreativeType.VIDEO)
        with self.assertRaises(Exception):
            ad.full_clean()

    def test_image_ad_requires_duration(self):
        ad = Ad(title='Sans durée', creative_type=Ad.CreativeType.IMAGE, image=_image_file())
        with self.assertRaises(Exception):
            ad.full_clean()
