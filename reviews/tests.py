from django.test import TestCase
from django.urls import reverse

from core.testing import make_user, make_wine

from .models import Review


class ReviewTests(TestCase):
    def setUp(self):
        self.wine = make_wine()
        self.user = make_user("ana.munoz@example.com")
        self.client.force_login(self.user)
        self.url = reverse("reviews:write", args=[self.wine.slug])

    def test_writing_twice_edits_the_same_review(self):
        self.client.post(self.url, {"rating": 4, "body": "Nice"})
        self.client.post(self.url, {"rating": 5, "body": "Even better the next day"})
        review = Review.objects.get()
        self.assertEqual(review.rating, 5)

    def test_rating_is_required(self):
        response = self.client.post(self.url, {"body": "No stars"})
        self.assertEqual(Review.objects.count(), 0)
        self.assertEqual(response.status_code, 200)

    def test_never_shows_the_full_email(self):
        review = Review.objects.create(user=self.user, wine=self.wine, rating=5, body="Great")
        self.assertEqual(review.author_name, "ana.munoz")
        self.assertNotContains(self.client.get(self.wine.get_absolute_url()), "ana.munoz@example.com")

    def test_only_the_author_can_delete(self):
        review = Review.objects.create(user=self.user, wine=self.wine, rating=5, body="Great")
        self.client.force_login(make_user("ben@example.com"))
        self.assertEqual(self.client.post(reverse("reviews:delete", args=[review.pk])).status_code, 404)
