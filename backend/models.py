from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.utils.translation import gettext_lazy as _
from django.contrib.auth.tokens import default_token_generator



class UserManager(BaseUserManager):
    """
    Миксин для управления пользователями
    """
    use_in_migrations = True

    def _create_user(self, email, password, **extra_fields):
        """
        Create and save a user with the given email and password.
        """
        if not email:
            raise ValueError('The given email must be set')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)
        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        # При создании суперпользователя используем username
        if 'username' not in extra_fields:
            extra_fields['username'] = email

        return self._create_user(email, password, **extra_fields)
    
    
class User(AbstractUser):
    username = models.CharField(max_length=150, blank=True, null=True)
    email = models.EmailField(_('email address'), unique=True)
    address = models.CharField(max_length=255, blank=True)
    phone_number = models.CharField(max_length=15, blank=True)
    login = models.CharField(max_length=150, blank=True, null=True, unique=True)
    token = models.CharField(max_length=255, blank=True, null=True)

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    def save(self, *args, **kwargs):
        if not self.pk:  # Проверяем, что объект только создается, а не обновляется
            self.token = '111'  # Устанавливаем токен
        super().save(*args, **kwargs)

    objects = UserManager()

    def __str__(self) -> str:
        return f'{self.first_name} {self.last_name}'
    
    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = "Список пользователей"
        ordering = ('email',)

class Supplier(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # другие поля, специфичные для поставщика



class Shop(models.Model):
    company_name = models.CharField(max_length=255)
    prise_list_url = models.URLField(verbose_name= 'Ссылка',null='True', blank=True)
    is_accepting_orders = models.BooleanField(verbose_name= 'принимает заказы', default=True)
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, null=True, blank=True)
    state = models.BooleanField(verbose_name='статус получения заказов', default=True)

    class Meta:
        verbose_name = 'Магазин'
        verbose_name_plural = "Список магазинов"
        ordering = ('-company_name',)

    def __str__(self):
        return self.company_name
    

class Category(models.Model):
    category_name = models.CharField(max_length=40, verbose_name='Название')
    shops = models.ManyToManyField(Shop, verbose_name='Магазины', related_name='categories', blank=True)

    def __str__(self) -> str:
        return self.category_name
    
    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = "Список категорий"
        ordering = ('-category_name',)



class Product(models.Model):
    product_name = models.CharField(max_length=255)
    category = models.ForeignKey(Category, verbose_name='Категория', related_name='products', blank=True, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, on_delete=models.CASCADE, default=1)  

    def __str__(self) -> str:
        return self.product_name

    class Meta:
        verbose_name = 'Продукт'
        verbose_name_plural = "Список продуктов"
        ordering  = ('-product_name',)



class ProductInfo(models.Model):

    model = models.CharField(max_length=80, verbose_name='Модель', blank=True)
    external_id = models.CharField(max_length=255, null=True, blank=True)
    product = models.ForeignKey(Product, verbose_name='Продукт', related_name='product_info', blank=True, on_delete=models.CASCADE)
    shop = models.ForeignKey(Shop, verbose_name='Магазин', related_name='product_info', blank=True, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(verbose_name='Цена', max_digits=10, decimal_places=2)
    price_rrc = models.DecimalField(verbose_name='Рекомендуемая розничная цена', max_digits=10, decimal_places=2)

    class Meta():
        verbose_name = 'Информация о продукте'
        verbose_name_plural = "Информационный список о продуктах"
        constraints = [
            models.UniqueConstraint(fields=['product', 'shop', 'external_id'], name='unique_product_info'),
        ]

    list_display = ('product', 'model', 'shop', 'quantity', 'price', 'price_rrc', 'is_shop_active')

    def is_shop_active(self, obj):
        return obj.shop.state
    is_shop_active.boolean = True
    is_shop_active.short_description = 'Активен'

    


class Parameter(models.Model):

    parameter_name = models.CharField(max_length=40, verbose_name='Название Параметра')

    class Meta():
        verbose_name = 'Имя параметра'
        verbose_name_plural = "Список имен параметров"
        ordering = ('-parameter_name',)
    
    def __str__(self):
        return self.parameter_name
        

    

class ProductParameter(models.Model):
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте', related_name='product_parameters', blank=True, on_delete=models.CASCADE)
    parameter = models.ForeignKey(Parameter, verbose_name='Параметр', related_name='product_parameters', blank=True, on_delete=models.CASCADE)
    value = models.CharField(verbose_name='Значение', max_length=100)

    
    class Meta:
        verbose_name = 'Параметр'
        verbose_name_plural = "Список параметров"
        constraints = [
            models.UniqueConstraint(fields=['product_info', 'parameter'], name='unique_product_parameter'),
        ]


class Contact(models.Model):
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='contacts', on_delete=models.CASCADE)
    city = models.CharField(max_length=50, verbose_name='Город')
    street = models.CharField(max_length=50, verbose_name='Улица')
    house = models.CharField(max_length=10, verbose_name='Дом')
    structure = models.CharField(max_length=10, verbose_name='Корпус', blank=True)
    building = models.CharField(max_length=10, verbose_name='Строение', blank=True)
    apartment = models.CharField(max_length=10, verbose_name='Квартира', blank=True)
    phone_number = models.CharField(max_length=15, verbose_name='Номер телефона', blank=True, null=True)

    class Meta:
        verbose_name = 'Контакты Пользователя'
        verbose_name_plural = "Список контактов пользователей"

    def __str__(self):
        return f'{self.city} {self.street} {self.house} {self.structure} {self.building} {self.apartment} {self.phone_number}'



class Order(models.Model):

    STATUS_CHOISES = [
        ('pending', 'Pending'),
        ('confirmed', 'Confirmed'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'),
        ('canceled', 'Canceled'),
    ]

    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='orders', blank=True, on_delete=models.CASCADE)
    status = models.CharField(verbose_name='Статус', choices=STATUS_CHOISES, max_length=20, default='pending')
    contact = models.ForeignKey(Contact, verbose_name='Контакт', related_name='orders', blank=True, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = "Список заказов"
        ordering = ('-created_at',)



class OrderItem(models.Model):
    order = models.ForeignKey(Order, verbose_name='Заказ', related_name='ordered_items', blank=True, on_delete=models.CASCADE)
    product_info = models.ForeignKey(ProductInfo, verbose_name='Информация о продукте', related_name='ordered_items', blank=True, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    price = models.DecimalField(max_digits=10, decimal_places=2)

    def get_total_price(self):
        return self.quantity * self.price
    
    class Meta:
        verbose_name = 'Заказанная позиция'
        verbose_name_plural = "Список заказанных позиций"
        constraints = [
            models.UniqueConstraint(fields=['order_id', 'product_info'], name='unique_order_item'),
        ]

    def __str__(self):
        return f'{self.product_info.product.product_name} - {self.quantity} шт. - {self.get_total_price()} руб.'
    


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)



class ConfirmEmailToken(models.Model):
    user = models.ForeignKey(User, verbose_name='Пользователь', related_name='confirm_email_tokens', blank=True, on_delete=models.CASCADE)
    token = models.CharField(_("Key"), max_length=64, db_index=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Токен подтверждения почты'
        verbose_name_plural = "Список токенов подтверждения почты"

    def generate_token(self):
        """ generates a pseudo random code using os.urandom and binascii.hexlify """
        return default_token_generator.make_token(self.user)
    
    def save(self, *args, **kwargs):
        if not self.token:
            self.token = self.generate_token()
        return super(ConfirmEmailToken, self).save(*args, **kwargs)
    
    def __str__(self):
        return "Password reset token for user {user}".format(user=self.user)