from django import forms
from django.test import Client, TestCase
from django.http.response import HttpResponse
from django.urls import reverse

from ..models import Group, Post, User

POSTS_PER_PAGE = 10


class PostViewTests(TestCase):
    @classmethod
    def setUpClass(cls):
        """Создаем двух авторов и две группы."""
        super().setUpClass()
        cls.author_1 = User.objects.create_user(username='author_1')
        cls.author_2 = User.objects.create_user(username='author_2')
        cls.group_1 = Group.objects.create(
            title='Группа_1',
            slug='group_1'
        )
        cls.group_2 = Group.objects.create(
            title='Группа_2',
            slug='group_2'
        )

    def setUp(self):
        """Создаем авторизованных клиентов и несколько постов."""
        self.authorized_client_1 = Client()
        self.authorized_client_1.force_login(self.author_1)
        self.authorized_client_2 = Client()
        self.authorized_client_2.force_login(self.author_2)
        self.post_1 = Post.objects.create(
            text='test_text_1',
            author=self.author_1,
            group=self.group_1
        )
        self.post_2 = Post.objects.create(
            text='test_text_2',
            author=self.author_2,
            group=None
        )
        self.post_3 = Post.objects.create(
            text='test_text_3',
            author=self.author_1,
            group=self.group_2
        )

    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_pages_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_list',
                    args=[self.group_1.slug]): 'posts/group_list.html',
            reverse('posts:profile',
                    args=[self.author_1.username]): 'posts/profile.html',
            reverse('posts:post_detail',
                    args=[self.post_1.id]): 'posts/post_detail.html',
            reverse('posts:post_create'): 'posts/create_post.html',
            reverse('posts:post_edit',
                    args=[self.post_1.id]): 'posts/create_post.html'
        }
        for reverse_name, template in templates_pages_names.items():
            with self.subTest(reverse_name=reverse_name):
                response = self.authorized_client_1.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def test_home_page_show_correct_context(self):
        """Шаблон index сформирован с правильным контекстом."""
        response = self.authorized_client_1.get(reverse('posts:index'))
        posts_from_context = response.context.get('page_obj').object_list
        expected_posts = list(Post.objects.all())
        self.assertEqual(posts_from_context, expected_posts,
                         'Главная страница выводит не все посты!'
                         )

    def test_group_list_page_show_correct_context(self):
        """Шаблон group_list сформирован с правильным контекстом."""
        response = self.authorized_client_1.get(
            reverse('posts:group_list', args=[self.group_2.slug])
        )
        posts_from_context = response.context.get('page_obj').object_list
        group_from_context = response.context.get('group')
        expected_posts = list(Post.objects.filter(group_id=self.group_2.id))
        self.assertEqual(posts_from_context, expected_posts,
                         'Посты в контексте имеют разное значение поле групп!'
                         )
        self.assertEqual(group_from_context, self.group_2,
                         'Страница группы отличается от группы из контекста!'
                         )

    def test_profile_page_show_correct_context(self):
        """Шаблон profile сформирован с правильным контекстом."""
        response = self.authorized_client_1.get(
            reverse('posts:profile', args=[self.author_1.username])
        )
        posts_from_context = response.context.get('page_obj').object_list
        author_from_context = response.context.get('author')
        expected_posts = list(Post.objects.filter(author_id=self.author_1.id))
        self.assertEqual(posts_from_context, expected_posts,
                         'Посты из контекста пренадлежать другому автору!'
                         )
        self.assertEqual(author_from_context, self.author_1,
                         'Автор из контекста не совпадает с профилем!'
                         )

    def test_post_detail_show_correct_context(self):
        """Шаблон post_detail сформирован с правильным контекстом."""
        response = self.authorized_client_1.get(
            reverse('posts:post_detail', args=[self.post_3.id])
        )
        post_from_context = response.context.get('post')
        number_posts_author = response.context.get('post_count')
        expected_number = Post.objects.filter(author=self.author_1).count()
        self.assertEqual(post_from_context, self.post_3,
                         'Пост из контекста не совпадает с ожидаемым!'
                         )
        self.assertEqual(number_posts_author, expected_number,
                         'Количество постов автора из контекста неверно!'
                         )

    def test_create_post_show_correct_context(self):
        """Шаблон create_post сформирован с правильным контекстом."""
        response = self.authorized_client_1.get(reverse('posts:post_create'))
        self._check_correct_form_from_context(response)

    def test_new_post_show_on_different_page(self):
        """Новый пост выводится на главной, в выбранной группе,
        и в профайле автора. Не выводится в других группах.
        """
        form_data = {
            'text': 'new_post',
            'group': self.group_1.id
        }
        url_names_assert_method = {
            reverse('posts:index'): self.assertEqual,
            reverse('posts:group_list',
                    args=[self.group_1.slug]): self.assertEqual,
            reverse('posts:profile',
                    args=[self.author_1.username]): self.assertEqual,
            reverse('posts:group_list',
                    args=[self.group_2.slug]): self.assertNotEqual
        }
        self.authorized_client_1.post(
            reverse('posts:post_create'),
            data=form_data
        )
        new_post = Post.objects.latest('id')
        for address, assert_method in url_names_assert_method.items():
            with self.subTest(address=address):
                response = self.authorized_client_1.get(address, follow=True)
                last_post_on_page = response.context.get('page_obj')[0]
                assert_method(last_post_on_page, new_post)

    def test_post_edit_show_correct_context(self):
        """Шаблон страницы post_edit сформирован с правильным контекстом."""
        response = self.authorized_client_1.get(
            reverse('posts:post_edit', args=[self.post_1.id])
        )
        self._check_correct_form_from_context(response)

    def _check_correct_form_from_context(self, response: HttpResponse) -> None:
        """Проверяем корректность формы передаваемой в контексте."""
        form_fields = {
            'text': forms.fields.CharField,
            'group': forms.fields.ChoiceField
        }
        for value, expected in form_fields.items():
            with self.subTest(value=value):
                form_field = response.context.get('form').fields.get(value)
                self.assertIsInstance(form_field, expected)


class PaginatorViewsTest(TestCase):
    @classmethod
    def setUpClass(cls):
        """Создаем автора и группу."""
        super().setUpClass()
        cls.author = User.objects.create_user(username='author_1')
        cls.group = Group.objects.create(
            title='Тестовая группа',
            slug='group_test'
        )

    def setUp(self):
        """Создаем клиента и 15 постов."""
        self.client = Client()
        self.number_create_posts = 15
        posts = []
        for i in range(self.number_create_posts):
            posts.append(Post.objects.create(
                text=f'test_text_{i}',
                author=self.author,
                group=self.group))

    def test_index_page(self):
        """Проверяет пагинацию главной страницы."""
        self._check_correct_pagination(reverse('posts:index'), POSTS_PER_PAGE)
        self._check_correct_pagination(
            reverse('posts:index') + '?page=2',
            self.number_create_posts % POSTS_PER_PAGE
        )

    def test_group_list_page(self):
        """Проверяет пагинацию страницы списка групп."""
        self._check_correct_pagination(
            reverse('posts:group_list', args=[self.group.slug]),
            POSTS_PER_PAGE
        )
        self._check_correct_pagination(
            reverse('posts:group_list', args=[self.group.slug]) + '?page=2',
            self.number_create_posts % POSTS_PER_PAGE
        )

    def test_profile_page(self):
        """Проверяет пагинацию страницы профиля автора."""
        self._check_correct_pagination(
            reverse('posts:profile', args=[self.author.username]),
            POSTS_PER_PAGE
        )
        self._check_correct_pagination(
            reverse('posts:profile', args=[self.author.username]) + '?page=2',
            self.number_create_posts % POSTS_PER_PAGE
        )

    def _check_correct_pagination(self, url_page: str, expected: int) -> None:
        """Сравнивает количество постов на запрошенной странице с ожидаемым
        результатом.
        """
        response = self.client.get(url_page)
        number_posts_on_page = len(response.context['page_obj'])
        self.assertEqual(number_posts_on_page, expected)
