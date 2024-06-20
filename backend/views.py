from django.shortcuts import render
import yaml
import requests
import json
from django.contrib.auth.views import PasswordResetView, PasswordResetConfirmView
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views import View
from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer
from django.http import JsonResponse
from django.contrib.auth import authenticate, login
from django.contrib.auth.views import PasswordResetView
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.contrib.auth import get_user_model
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.permissions import AllowAny

from rest_framework.views import APIView
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ObjectDoesNotExist
from django.core.exceptions import ValidationError
from django.core.validators import URLValidator
from django.db import IntegrityError
from django.db.models import Q, Sum, F
from django.http import JsonResponse
from requests import get
from rest_framework.authtoken.models import Token
from rest_framework.generics import ListAPIView
from rest_framework.response import Response
from rest_framework.views import APIView    
from ujson import loads as load_json
from rest_framework import status
import logging
from .serializers import PriceListUploadSerializer, UserSerializer, CategorySerializer, ShopSerializer, ProductSerializer, ProductInfoSerializer, ProductParameterSerializer, OrderSerializer, RegisterAccountSerializer, OrderItemCreateSerializer, ContactSerializer
from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact, User, ConfirmEmailToken




logger = logging.getLogger(__name__)


class FixedTokenAuthentication(BaseAuthentication):
    def authenticate(self, request):
        token = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[-1]
        if token == '111':
            return (None, None)  # Возвращаем (None, None), чтобы указать, что пользователь аутентифицирован
        raise AuthenticationFailed('Invalid token')



def strtobool(val):
    """Convert a string representation of truth to true (1) or false (0).

    True values are 'y', 'yes', 't', 'true', 'on', and '1'; false values
    are 'n', 'no', 'f', 'false', 'off', and '0'.  Raises ValueError if
    'val' is anything else.
    """
    val = val.lower()
    if val in ('y', 'yes', 't', 'true', 'on', '1'):
        return 1
    elif val in ('n', 'no', 'f', 'false', 'off', '0'):
        return 0
    else:
        raise ValueError("invalid truth value %r" % (val,))




class HomeView(View):

   def get(self, request):
        return HttpResponse("Hello, this is the home page!")


@method_decorator(csrf_exempt, name='dispatch')
class CustomPasswordResetView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            email = data.get('email')

            if not email:
                return JsonResponse({"status": "error", "message": "Email is required."}, status=400)

            User = get_user_model()
            user = User.objects.filter(email=email).first()

            if not user:
                return JsonResponse({"status": "error", "message": "User with this email does not exist."}, status=404)

            # Здесь должна быть логика сброса пароля, например, отправка письма
            # В тестовом примере просто возвращаем JSON с фиксированным токеном
            return JsonResponse({"status": "success", "token": "111", "email": email}, status=200)

        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data."}, status=400)
        

@method_decorator(csrf_exempt, name='dispatch')
class CustomPasswordResetConfirmView(View):
    def post(self, request):
        try:
            data = json.loads(request.body)
            token = data.get('token')
            password = data.get('password')
            email = data.get('email')  # Добавляем проверку на наличие email

            if not token or not password or not email:
                return JsonResponse({"status": "error", "message": "Token, password, and email are required."}, status=400)

            User = get_user_model()
            user = User.objects.filter(email=email).first()

            if user:
                user.set_password(password)
                user.save()
                # Автоматически логиним пользователя после сброса пароля
                user = authenticate(request, username=user.username, password=password)
                if user is not None:
                    login(request, user)
                return JsonResponse({"status": "success", "message": "Password reset successful."}, status=200)
            else:
                return JsonResponse({"status": "error", "message": "User not found or invalid token."}, status=400)

        except json.JSONDecodeError:
            return JsonResponse({"status": "error", "message": "Invalid JSON data."}, status=400)
        

class PriceListUploadView(APIView):
    def post(self, request):
        serializer = PriceListUploadSerializer(data=request.data)
        if serializer.is_valid():
            filePath = serializer.validated_data['filePath']
            with open(filePath, 'r', encoding='utf-8') as file:
                try:
                    data = yaml.safe_load(file)
                    self.update_shop_data(data)
                    return Response({'status': 'success'}, status=200)
                except yaml.YAMLError as e:
                    return Response({'error': 'Error parsing YAML file', 'details': str(e)}, status=400)
        else:
            return Response(serializer.errors, status=400)


    def update_shop_data(self, data):
        # Update shop information
        shop, created = Shop.objects.get_or_create(company_name=data['shop'])

        # Update categories
        categories_map = {}
        for category in data['categories']:
            category_obj, created = Category.objects.get_or_create(id=category['id'], category_name=category['category_name'])
            categories_map[category['id']] = category_obj
            if created:
                shop.categories.add(category_obj)

        # Update products
        for product in data['goods']:
            category_obj = categories_map[product['category']]
            product_obj, created = Product.objects.get_or_create(id=product['id'], product_name=product['product_name'], category=category_obj)

            external_id = product.get('external_id', 'default_value')

            product_info = ProductInfo.objects.create(
                product_id=product_obj.id,
                shop_id=shop.id,
                quantity=product['quantity'],
                price=product['price'],
                price_rrc=product['price_rrc'],
                external_id=external_id
            )

            # Update parameters
            for name, value in product['parameters'].items():
                parameter_object, _ = Parameter.objects.get_or_create(parameter_name=name)
                ProductParameter.objects.create(product_info_id=product_info.id, parameter_id=parameter_object.id, value=value)

        return Response({"status": "success"}, status=status.HTTP_200_OK)
        




class RegisterAccount(APIView):
    
    
    """
    Для регистрации покупателей
    """

    # Регистрация методом POST
    
    def post(self, request, *args, **kwargs):
        """
            Process a POST request and create a new user.

            Args:
                request (Request): The Django request object.

            Returns:
                JsonResponse: The response indicating the status of the operation and any errors.
        """
        # проверяем обязательные аргументы
        if {'email', 'password', 'first_name', 'last_name'}.issubset(request.data):
            # валидируем пароль
            try:
                validate_password(request.data['password'])
            except Exception as password_error:
                return Response({"status": "error", "errors": str(password_error)}, status=status.HTTP_400_BAD_REQUEST)
            else:
                # проверяем данные для уникальности имени пользователя
                user_serializer = RegisterAccountSerializer(data=request.data)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    print(f"Пользователь с именем {user.first_name}, фамилией {user.last_name} и емэйлом {user.email} успешно зарегистрирован в базе.")
                    # Генерация токена для подтверждения email
                    # token = secrets.token_urlsafe(32)
                    # ConfirmEmailToken.objects.create(user=user, token=token)
                    # Возвращаем сериализованные данные пользователя, включая id
                    return Response(user_serializer.data, status=status.HTTP_201_CREATED)
                else:
                    return Response({"status": "error", "errors": user_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        else:
            return Response({"status": "error", "errors": "Не указаны все необходимые аргументы"}, status=status.HTTP_400_BAD_REQUEST)
    

    
class ConfirmAccount(APIView):
    """
    Класс для подтверждения почтового адреса
    """

    # Регистрация методом POST
    def post(self, request, *args, **kwargs):
        """
                Подтверждает почтовый адрес пользователя.

                Args:
                - request (Request): The Django request object.
                - token (str): The confirmation token.
                - email (str): The user's email address.
                Return:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        
        logger.info(f"Received request data: {request.data}")

          # Проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):
            User = get_user_model()
            try:
                user = User.objects.get(email=request.data['email'])
                token = ConfirmEmailToken.objects.get(user=user, token=request.data['token'])
                user.is_active = True
                user.save()
                token.delete()
                return Response({"status": "token check is success"}, status=status.HTTP_200_OK)
            except (User.DoesNotExist, ConfirmEmailToken.DoesNotExist):
                return Response({"status": "error", "errors": "Неверный токен или email"}, status=status.HTTP_400_BAD_REQUEST)
        return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=status.HTTP_400_BAD_REQUEST)
    


class AccountDetails(APIView):

    """
    Класс для получения информации о пользователе
    """


    def get(self, request, user_id, *args, **kwargs):
        # Вывод заголовков запроса для отладки
        print("Headers of the request:", request.headers)
        token = request.headers.get('Authorization', '').replace('Token ', '')
        print("Extracted token before replace:", request.headers.get('Authorization'))
        print("Extracted token:", token)  # Отладочный вывод для проверки извлечения токена

        try:
            user = User.objects.get(id=user_id)
            print("Database token:", user.token)  # Отладочный вывод для пр
            print("Request token:", token)
            # Проверяем, соответствует ли токен пользователя
            if user.token == token:
                serializer = UserSerializer(user)
                return Response(serializer.data, status=status.HTTP_200_OK)
            else:
                return Response({'Status': False, 'Error': 'Invalid token'}, status=status.HTTP_403_FORBIDDEN)
        except User.DoesNotExist:
            return Response({'Status': False, 'Error': 'User not found'}, status=status.HTTP_404_NOT_FOUND)


    def post(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if {'email', 'first_name', 'last_name'}.issubset(request.data):
            user_serializer = UserSerializer(request.user, data=request.data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
                return JsonResponse({"status": "success"}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({"status": "error", "errors": user_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({"status": "error", "errors": "Не указаны все необходимые аргументы"}, status=status.HTTP_400_BAD_REQUEST)
    

class LoginAccount(APIView):
    """
        Класс для авторизации пользователей
    """
    def post(self, request, *args, **kwargs):
         """
                Authenticate a user.

                Args:
                    request (Request): The Django request object.

                Returns:
                    JsonResponse: The response indicating the status of the operation and any errors.
                """
         # проверяем обязательные аргументы
         if {'email', 'password'}.issubset(request.data):
            user = authenticate(email=request.data['email'], password=request.data['password'])
            if user:
                login(request, user)
                return Response({"status": "success"}, status=status.HTTP_200_OK)
            else:
                return Response({"status": "error", "errors": "Неверный логин или пароль"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"status": "error", "errors": "Не указаны все необходимые аргументы"}, status=status.HTTP_400_BAD_REQUEST)
    

class CategoryView(APIView):

    """
    Класс для просмотра категорий
    """
     
    serializer_class = CategorySerializer
    queryset = Category.objects.all()

    def get(self, request):
        categories = Category.objects.all()
        serializer = self.serializer_class(categories, many=True)
        return Response(serializer.data)


class ShopView(APIView):

    """
    Класс для просмотра списка магазинов
    """

    serializer_class = ShopSerializer
    queryset = Shop.objects.all() 

    def get(self, request):
        shops = Shop.objects.all()
        serializer = self.serializer_class(shops, many=True)
        return Response(serializer.data)


class ProductInfoView(APIView):
     """
        A class for searching products.

        Methods:
        - get: Retrieve the product information based on the specified filters.

        Attributes:
        - None
        """
     
     def get(self, request: Request, *args, **kwargs):
        print("Received GET request for products")
        queryset = ProductInfo.objects.filter(shop__state=True).select_related('product__category', 'product__shop').prefetch_related('product_parameters__parameter').distinct()
        print(f"Queryset: {queryset}")
        serializer = ProductInfoSerializer(queryset, many=True)
        print(f"Serialized data: {serializer.data}")
        return Response(serializer.data, status=status.HTTP_200_OK)



class BasketView(APIView):
    authentication_classes = []  # Отключаем аутентификацию
    permission_classes = [AllowAny]  # Разрешаем доступ любому пользователю

    def get(self, request, user_id):
        basket = Order.objects.filter(user_id=user_id, status='basket')
        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    def post(self, request, user_id):
        items_data = request.data.get('items')
        if not items_data:
            return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=400)
        
        # Получаем или создаем контакт пользователя
        contact, _ = Contact.objects.get_or_create(user_id=user_id)
        
        # Создаем заказ в корзине
        basket, _ = Order.objects.get_or_create(user_id=user_id, status='basket', contact=contact)
        
        objects_created = 0
        for item_data in items_data:
            # Убедитесь, что указаны все необходимые поля для создания элемента заказа
            product_info_id = item_data.get('product_info')
            quantity = item_data.get('quantity')
            if not product_info_id or not quantity:
                return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=400)
            
            # Получаем информацию о продукте
            try:
                product_info = ProductInfo.objects.get(id=product_info_id)
            except ProductInfo.DoesNotExist:
                return Response({'Status': False, 'Errors': 'Информация о продукте не найдена'}, status=400)
            
            # Убедитесь, что цена продукта существует
            if not product_info.price:
                return Response({'Status': False, 'Errors': 'Цена продукта не определена'}, status=400)
            
            # Создаем элемент заказа
            order_item = OrderItem.objects.create(order=basket, product_info=product_info, quantity=quantity, price=product_info.price)
            objects_created += 1
        
        return Response({'Status': True, 'Создано объектов': objects_created})
        

    def put(self, request, user_id):
        items_dict = request.data.get('items')
        if not items_dict:
            return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=400)
        basket, _ = Order.objects.get_or_create(user_id=user_id, status='basket')
        objects_updated = 0
        for order_item in items_dict:
            if 'id' in order_item and 'quantity' in order_item:
                objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(quantity=order_item['quantity'])
        return Response({'Status': True, 'Обновлено объектов': objects_updated})

    def delete(self, request, user_id):
        items_list = request.data.get('items')
        if not items_list:
            return Response({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=400)
        basket, _ = Order.objects.get_or_create(user_id=user_id, status='basket')
        deleted_count = OrderItem.objects.filter(order_id=basket.id, id__in=items_list).delete()[0]
        return Response({'Status': True, 'Удалено объектов': deleted_count})




class PartnerState(APIView):
    def get(self, request, *args, **kwargs):
        shop_id = kwargs.get('shop_id')
        if not shop_id:
            return JsonResponse({'Status': False, 'Error': 'Не указан идентификатор магазина'}, status=400)

        try:
            shop = Shop.objects.get(id=shop_id)
            serializer = ShopSerializer(shop)
            return Response(serializer.data)
        except Shop.DoesNotExist:
            return JsonResponse({'Status': False, 'Error': 'Магазин не найден'}, status=404)

    def post(self, request, *args, **kwargs):
        print(request.data)  # Добавьте эту строку для отладки
        shop_id = request.data.get('shop_id')
        state = request.data.get('state')

        if not shop_id or not state:
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'}, status=400)

        try:
            shop = Shop.objects.get(id=shop_id)
            shop.state = state
            shop.save()
            return JsonResponse({'Status': True})
        except Shop.DoesNotExist:
            return JsonResponse({'Status': False, 'Errors': 'Магазин не найден'}, status=404)
        except Exception as error:
            return JsonResponse({'Status': False, 'Errors': str(error)})
            
        

class PartnerOrders(APIView):

    def get(self, request, *args, **kwargs):
        # Проверяем, что токен в заголовке запроса равен '111'
        token = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[-1]
        if token != '111':
            return Response({'error': 'Invalid token'}, status=status.HTTP_403_FORBIDDEN)

        # Получаем shop_id из параметров запроса
        shop_id = kwargs.get('shop_id')
        if not shop_id:
            return Response({'error': 'Shop ID is required'}, status=status.HTTP_400_BAD_REQUEST)

        # Фильтруем заказы по shop_id
        orders = Order.objects.filter(shop_id=shop_id)
        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)

            

class ContactView(APIView):
    renderer_classes = [JSONRenderer]

    def dispatch(self, request, *args, **kwargs):
        try:
            # Проверяем наличие заголовка Authorization и его содержимое
            auth_header = request.META.get('HTTP_AUTHORIZATION')
            if auth_header and auth_header.startswith('Bearer 111'):
                user_id = kwargs.get('user_id', None)
                if user_id:
                    try:
                        request.user = get_user_model().objects.get(id=user_id)
                    except get_user_model().DoesNotExist:
                        return Response({'detail': 'User not found'}, status=status.HTTP_404_NOT_FOUND)
                else:
                    return Response({'detail': 'User ID is required'}, status=status.HTTP_400_BAD_REQUEST)
            else:
                return Response({'detail': 'Authentication required'}, status=status.HTTP_401_UNAUTHORIZED)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return super().dispatch(request, *args, **kwargs)
    

    def get(self, request, user_id, *args, **kwargs):
        try:
            contacts = Contact.objects.filter(user_id=user_id)
            serializer = ContactSerializer(contacts, many=True)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'detail': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


    def post(self, request, user_id, *args, **kwargs):
        try:
            user = get_user_model().objects.get(id=user_id)
        except ObjectDoesNotExist:
            return Response({'Status': False, 'Errors': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Проверяем, существует ли уже контакт для пользователя
        contact = Contact.objects.filter(user=user).first()
        if contact:
            return Response({'Status': False, 'Errors': 'Contact already exists for this user'}, status=status.HTTP_409_CONFLICT)

        # Создаем новый контакт
        serializer = ContactSerializer(data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save(user=user)
            return Response({'Status': True}, status=status.HTTP_201_CREATED)
        return Response({'Status': False, 'Errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)

    def put(self, request, user_id, *args, **kwargs):
        try:
            # Получаем пользователя по user_id
            user = get_user_model().objects.get(id=user_id)
        except ObjectDoesNotExist:
            return Response({'Status': False, 'Errors': 'User not found'}, status=status.HTTP_404_NOT_FOUND)

        # Получаем контакт пользователя
        contact = Contact.objects.filter(user=user).first()

        # Если контакт не существует, создаем новый
        if not contact:
            contact = Contact(user=user)

        # Сериализуем данные запроса с частичным обновлением
        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            # Сохраняем обновленные данные
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Возвращаем ошибку валидации
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, user_id, *args, **kwargs):
        try:
            contacts = Contact.objects.filter(user_id=user_id)

        # Удаляем все контакты пользователя
            contacts.delete()

            return Response({'Status': True}, status=status.HTTP_204_NO_CONTENT)
        except Contact.DoesNotExist:
            return Response({'Status': False, 'Errors': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)
    
    
    def patch(self, request, user_id, *args, **kwargs):
        try:
            user = get_user_model().objects.get(id=user_id)
            contact = Contact.objects.get(user=user)
        except (ObjectDoesNotExist, Contact.DoesNotExist):
            return Response({'Status': False, 'Errors': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)

        # Обновляем контакт
        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({'Status': True, 'data': serializer.data}, status=status.HTTP_200_OK)
        return Response({'Status': False, 'Errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



class OrderView(APIView):
    """
    A class for managing orders.
    Methods:
    - get: Retrieve the orders associated with the authenticated user.
    - post: Create a new order for the authenticated user.
    - put: Update the details of a specific order.
    - delete: Delete a specific order.

    Attributes:
    - None
    """
     # получить мои заказы

    def get(self, request, user_id=None):
        """
        Retrieve the details of user orders.

        Args:
        - request (Request): The Django request object.
        - user_id (int, optional): The ID of the user for whom the orders are being retrieved.

        Returns:
        - Response: The response containing the details of the order.
        """
        if user_id:
            # Retrieve orders for a specific user
            try:
                orders = Order.objects.filter(user_id=user_id)
                serializer = OrderSerializer(orders, many=True)
                return Response(serializer.data)
            except Order.DoesNotExist:
                return Response({'error': 'No orders found for this user'}, status=404)
        else:
            # Retrieve orders for the authenticated user
            if not request.user.is_authenticated:
                return Response({'Status': False, 'Error': 'Log in required'}, status=403)
            
            orders = Order.objects.filter(user_id=request.user.id).exclude(state='basket').prefetch_related(
                'ordered_items__product_info__product__category',
                'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
                total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)
        
    
    # разместить заказ из корзины

    def post(self, request, user_id, *args, **kwargs):
        """
        Create a new order and send a notification.

        Args:
        - request (Request): The Django request object.
        - user_id (int): The ID of the user for whom the order is being placed.

        Returns:
        - Response: The response indicating the status of the operation and any errors.
        """

        # Проверяем наличие токена в заголовке запроса
        token = request.META.get('HTTP_AUTHORIZATION', '').split('Bearer ')[-1]
        if token != '111':
            return Response({'Status': False, 'Error': 'Invalid token'}, status=403)

        # Проверяем наличие необходимых данных в запросе
        if {'ordered_items'}.issubset(request.data):
            try:
                # Получаем пользователя и связанный с ним контакт
                user = User.objects.get(id=user_id)
                contact = user.contacts.first()  # Предполагаем, что у пользователя есть хотя бы один контакт

                # Создаем новый заказ
                order = Order.objects.create(user=user, contact=contact)

                # Создаем позиции заказа
                for item_data in request.data['ordered_items']:
                    product_info = ProductInfo.objects.get(id=item_data['product_info']['id'])
                    OrderItem.objects.create(
                        order=order,
                        product_info=product_info,
                        quantity=item_data['quantity'],
                        price=product_info.price
                    )

                # Возвращаем успешный статус
                return Response({'Status': True}, status=201)

            except Exception as e:
                return Response({'Status': False, 'Error': str(e)}, status=400)

        return Response({'Status': False, 'Error': 'Missing required data'}, status=400)



class UserOrdersView(APIView):

    def get(self, request, user_id):
        try:
            # Получаем все заказы пользователя
            orders = Order.objects.filter(user_id=user_id)
            serializer = OrderSerializer(orders, many=True)
            return Response(serializer.data)
        except Order.DoesNotExist:
            return Response({'error': 'No orders found for this user'}, status=404)



class UserListView(APIView):
    def get(self, request):
        try:
            users = User.objects.all()
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)