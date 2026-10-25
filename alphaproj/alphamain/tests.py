from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import News

User = get_user_model()


class AuthTests(TestCase):
    password = 'Secure-Hackathon!9841'

    def registration(self, **changes):
        data = {'name': 'Иван Иванович', 'email': 'director@example.com',
                'password1': self.password, 'password2': self.password}
        data.update(changes)
        return self.client.post(reverse('register'), data)

    def test_registration_hashes_password_and_logs_in(self):
        response = self.registration(email='Director@Example.COM')
        self.assertRedirects(response, reverse('home'))
        user = User.objects.get(username='director@example.com')
        self.assertEqual(user.email, 'director@example.com')
        self.assertEqual(user.first_name, 'Иван Иванович')
        self.assertNotEqual(user.password, self.password)
        self.assertTrue(user.check_password(self.password))
        self.assertEqual(int(self.client.session['_auth_user_id']), user.pk)

    def test_registered_full_name_is_shown_immediately_and_after_login(self):
        full_name = 'Петрова Анна Сергеевна'
        self.registration(name=full_name)
        for revisit in (False, True):
            if revisit:
                self.client.post(reverse('logout'))
                self.client.post(reverse('login'), {'username': 'director@example.com', 'password': self.password})
            response = self.client.get(reverse('home'))
            self.assertEqual(response.context['account_data']['name'], full_name)
            self.assertContains(response, f'id="greeting">{full_name}</span>')
            self.assertContains(response, f'id="user-name">{full_name}</strong>')
            self.assertContains(response, f'value="{full_name}" readonly')

    def test_account_name_supports_standard_first_and_last_name(self):
        user = User.objects.create_user(username='name@example.com', first_name='Анна', last_name='Петрова')
        self.client.force_login(user)
        self.assertEqual(self.client.get('/').context['account_data']['name'], 'Анна Петрова')

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user(username='director@example.com', email='director@example.com', password=self.password)
        response = self.registration(email='DIRECTOR@example.com')
        self.assertContains(response, 'Аккаунт с таким email уже существует.')
        self.assertEqual(User.objects.count(), 1)

    def test_invalid_registrations_do_not_create_users(self):
        for changes in ({'password2': 'different'}, {'password1': '123', 'password2': '123'},
                        {'email': 'not-email'}, {'name': '   '}):
            with self.subTest(changes=changes):
                self.assertEqual(self.registration(**changes).status_code, 200)
                self.assertEqual(User.objects.count(), 0)

    def test_login_logout_and_protected_feed(self):
        User.objects.create_user(username='director@example.com', password=self.password)
        response = self.client.get('/')
        self.assertRedirects(response, '/login/?next=/')
        self.assertNotContains(response, 'news-data', status_code=302)
        response = self.client.post(reverse('login'), {'username': 'DIRECTOR@example.com', 'password': self.password})
        self.assertRedirects(response, '/')
        self.assertContains(self.client.get('/'), 'account-data')
        self.assertEqual(self.client.get(reverse('logout')).status_code, 405)
        self.assertRedirects(self.client.post(reverse('logout')), reverse('login'))
        self.assertNotIn('_auth_user_id', self.client.session)
        self.assertRedirects(self.client.get('/'), '/login/?next=/')

    def test_routes_have_one_canonical_address(self):
        for name, url in (('home', '/'), ('login', '/login/'),
                          ('register', '/register/'), ('logout', '/logout/')):
            with self.subTest(name=name):
                self.assertEqual(reverse(name), url)
        for url in ('/v1/', '/v1/login/', '/v1/register/', '/v1/logout/'):
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 404)

    def test_authenticated_users_skip_account_pages(self):
        user = User.objects.create_user(username='director@example.com', password=self.password)
        self.client.force_login(user)
        for name in ('login', 'register'):
            with self.subTest(name=name):
                self.assertRedirects(self.client.get(reverse(name)), '/')

    def test_wrong_password_and_inactive_user(self):
        user = User.objects.create_user(username='director@example.com', password=self.password)
        for password in ('wrong', self.password):
            if password == self.password:
                user.is_active = False
                user.save()
            response = self.client.post(reverse('login'), {'username': user.username, 'password': password})
            self.assertEqual(response.status_code, 200)
            self.assertNotIn('_auth_user_id', self.client.session)

    def test_external_next_does_not_redirect_off_site(self):
        User.objects.create_user(username='director@example.com', password=self.password)
        response = self.client.post(reverse('login'), {'username': 'director@example.com', 'password': self.password, 'next': 'https://example.org/'})
        self.assertRedirects(response, '/')

    def test_csrf_required_for_authentication(self):
        client = Client(enforce_csrf_checks=True)
        for name in ('register', 'login', 'logout'):
            with self.subTest(name=name):
                self.assertEqual(client.post(reverse(name), {}).status_code, 403)

    def test_account_pages_use_shared_design(self):
        for name in ('register', 'login'):
            response = self.client.get(reverse(name))
            self.assertTemplateUsed(response, 'alphamain/base.html')
            self.assertTemplateUsed(response, 'alphamain/auth_base.html')
            self.assertContains(response, 'alphamain/feed.css')
            self.assertContains(response, 'csrfmiddlewaretoken')


class NewsTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='reader@example.com', password='Safe-Pass!21576')
        self.client.force_login(self.user)

    def create_news(self, **changes):
        fields = {'title': 'Новая промышленная программа', 'summary': 'Краткое описание события',
                  'content': 'Полный текст события', 'source_name': 'Тестовый источник',
                  'source_url': 'https://example.com/article', 'status': News.Status.PUBLISHED}
        fields.update(changes)
        return News.objects.create(**fields)

    def test_only_current_published_news_are_in_feed(self):
        published = self.create_news()
        self.create_news(source_url='https://example.com/draft', status=News.Status.DRAFT)
        self.create_news(source_url='https://example.com/archive', status=News.Status.ARCHIVED)
        self.create_news(source_url='https://example.com/future', published_at=timezone.now()+timedelta(days=1))
        response = self.client.get('/')
        self.assertEqual([row['id'] for row in response.context['news_data']], [published.pk])
        self.assertTrue(response.context['has_news'])
        self.assertTemplateUsed(response, 'alphamain/base.html')

    def test_empty_database_keeps_demo_mode(self):
        for url in ('/',):
            response = self.client.get(url)
            self.assertEqual(response.status_code, 200)
            self.assertFalse(response.context['has_news'])
            self.assertContains(response, 'Демонстрационные данные')

    def test_article_text_is_serialized_safely(self):
        self.create_news(title='</script><script>alert(1)</script>')
        response = self.client.get('/')
        self.assertNotContains(response, '</script><script>alert(1)</script>')
        self.assertContains(response, r'\u003C/script\u003E')

    def test_bank_analysis_requires_source(self):
        article = News(title='Заголовок', summary='Кратко', content='Текст', source_name='Источник',
                       source_url='https://example.com/test', bank_analysis='Позиция банка')
        with self.assertRaises(ValidationError):
            article.full_clean()
        article.bank_source_url = 'https://example.com/bank'
        article.full_clean()

    def test_source_url_must_be_unique_and_http(self):
        self.create_news()
        article = News(title='Повтор', summary='Кратко', content='Текст', source_name='Источник', source_url='https://example.com/article')
        with self.assertRaises(ValidationError):
            article.full_clean()
        article.source_url = 'javascript:alert(1)'
        with self.assertRaises(ValidationError):
            article.full_clean()
