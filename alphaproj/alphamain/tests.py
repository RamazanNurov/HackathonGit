from django.test import SimpleTestCase
from django.urls import reverse


class FeedTests(SimpleTestCase):
    def test_feed_pages(self):
        for url in ('/', '/v1/'):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, 'alphamain/feed.html')
                self.assertContains(response, 'id="profile-form"')
                self.assertContains(response, 'alphamain/feed.js')

    def test_registration_is_preserved(self):
        self.assertEqual(self.client.get(reverse('register')).status_code, 200)
