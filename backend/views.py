from django.shortcuts import render
import yaml
#from distutils.util import strtobool

from django.views import View
from django.http import HttpResponse
from rest_framework.renderers import JSONRenderer
import secrets


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
from .serializers import PriceListUploadSerializer, UserSerializer, CategorySerializer, ShopSerializer, ProductSerializer, ProductInfoSerializer, ProductParameterSerializer, OrderSerializer, RegisterAccountSerializer, OrderItemSerializer, ContactSerializer
from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact, User, ConfirmEmailToken




logger = logging.getLogger(__name__)



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



class PriceListUploadView(APIView):


    def post(self, request, *args, **kwargs):
        serializer = PriceListUploadSerializer(data=request.data)
        if serializer.is_valid():
            file = serializer._validated_data['file']
            try:
                data = yaml.safe_load(file)
                self.update_shop_data(data)
                return Response({"status": "success"}, status=status.HTTP_200_OK)
            except yaml.YAMLError as e:
                return Response({"status": "success"}, status=status.HTTP_400_BAD_REQUEST)
            except Exception as e:
                return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

    def update_shop_data(self ,data):
        
         # Update shop information
        shop, created = Shop.objects.get_or_create(company_name=data['shop'])

        # Update categories
        categories_map = {}
        for category in data['categories']:
            category_obj, created = Category.objects.get_or_create(id=category['id'], name=category['name'])
            categories_map[category['id']] = category_obj
            if created:
                shop.categories.add(category_obj)

        # Update products  
        for product in data['goods']:
            category_obj = categories_map[product['category_id']]
            product_obj, created = Product.objects.get_or_create(id=product['id'], name=product['name'], category=category_obj)

            product_info = ProductInfo.objects.create(product_id=product_obj.id,shop_id=shop.id, quantity=product['quantity'], price=product['price'], price_rrc=product['price_rrc'])

            # Update parameters 
            for name, value in product['parameters'].items():
                parameter_object, _ = Parameter.objects.get_or_create(name=name)
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
                return JsonResponse({"status": "success"}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({"status": "error", "errors": "Неверный логин или пароль"}, status=status.HTTP_400_BAD_REQUEST)
         return JsonResponse({"status": "error", "errors": "Не указаны все необходимые аргументы"}, status=status.HTTP_400_BAD_REQUEST)
    

class CategoryView(APIView):

    """
    Класс для просмотра категорий
    """
     
    serializer_class = CategorySerializer
    queryset = Category.objects.all()


class ShopView(APIView):

    """
    Класс для просмотра списка магазинов
    """

    serializer_class = ShopSerializer
    queryset = Shop.objects.filter(state=True)


class ProductInfoView(APIView):
     """
        A class for searching products.

        Methods:
        - get: Retrieve the product information based on the specified filters.

        Attributes:
        - None
        """
     
     def get(self, request: Request, *args, **kwargs):
        
        """
               Retrieve the product information based on the specified filters.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the product information.
        """
        query = Q(shop__state=True)
        shop_id = request.query_params.get('shop_id', None)
        category_id = request.query_params.get('category_id', None)

        if shop_id:
            query &= Q(shop_id=shop_id)

        if category_id:
            query &= Q(category_id=category_id)
            
        # фильтруем и отбрасываем дуликаты
        queryset = Product.objects.filter(query).select_related('shop', 'product__category').prefetch_related('product_parameters__parameter').distinct()



        serializer = ProductSerializer(queryset, many=True)
        return JsonResponse(serializer.data, status=status.HTTP_200_OK, safe=False)



class BasketView(APIView):
    """
    A class for managing the user's shopping basket.

    Methods:
    - get: Retrieve the items in the user's basket.
    - post: Add an item to the user's basket.
    - put: Update the quantity of an item in the user's basket.
    - delete: Remove an item from the user's basket.

    Attributes:
    - None
    """

    # получить корзину
    def get(self, request, *args, **kwargs):
        """
                Retrieve the items in the user's basket.

                Args:
                - request (Request): The Django request object.

                Returns:
                - Response: The response containing the items in the user's basket.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        basket = Order.objects.filter(
            user_id=request.user.id, state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(basket, many=True)
        return Response(serializer.data)

    # редактировать корзину
    def post(self, request, *args, **kwargs):
        """
               Add an items to the user's basket.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_created = 0
                for order_item in items_dict:
                    order_item.update({'order': basket.id})
                    serializer = OrderItemSerializer(data=order_item)
                    if serializer.is_valid():
                        try:
                            serializer.save()
                        except IntegrityError as error:
                            return JsonResponse({'Status': False, 'Errors': str(error)})
                        else:
                            objects_created += 1

                    else:

                        return JsonResponse({'Status': False, 'Errors': serializer.errors})

                return JsonResponse({'Status': True, 'Создано объектов': objects_created})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # удалить товары из корзины
    def delete(self, request, *args, **kwargs):
        """
                Remove  items from the user's basket.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            items_list = items_sting.split(',')
            basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
            query = Q()
            objects_deleted = False
            for order_item_id in items_list:
                if order_item_id.isdigit():
                    query = query | Q(order_id=basket.id, id=order_item_id)
                    objects_deleted = True

            if objects_deleted:
                deleted_count = OrderItem.objects.filter(query).delete()[0]
                return JsonResponse({'Status': True, 'Удалено объектов': deleted_count})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

    # добавить позиции в корзину
    def put(self, request, *args, **kwargs):
        """
               Update the items in the user's basket.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        items_sting = request.data.get('items')
        if items_sting:
            try:
                items_dict = load_json(items_sting)
            except ValueError:
                return JsonResponse({'Status': False, 'Errors': 'Неверный формат запроса'})
            else:
                basket, _ = Order.objects.get_or_create(user_id=request.user.id, state='basket')
                objects_updated = 0
                for order_item in items_dict:
                    if type(order_item['id']) == int and type(order_item['quantity']) == int:
                        objects_updated += OrderItem.objects.filter(order_id=basket.id, id=order_item['id']).update(
                            quantity=order_item['quantity'])

                return JsonResponse({'Status': True, 'Обновлено объектов': objects_updated})
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})



class PartnerUpdate(APIView):
    
    """
       A class for managing partner state.

       Methods:
       - get: Retrieve the state of the partner.

       Attributes:
       - None
       """
    # получить текущий статус
    def get(self, request, *args, **kwargs):
        """
                Retrieve the state of the partner.

                Args:
                - request (Request): The Django request object.
                Returns:
                - Response: The response containing the state of the partner.

        """        
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)


        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)
    

    # Изменить текущий статус
    def post(self, request, *args, **kwargs):
        """
                Update the partner price list information.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        url = request.data.get('url')
        if url:
            validate_url = URLValidator()
            try:
                validate_url(url)
            except ValidationError as e:
                return JsonResponse({'Status': False, 'Error': str(e)})
            else:
                stream = get(url).content

                data = load_yaml(stream, Loader=Loader)

                shop, _ = Shop.objects.get_or_create(name=data['shop'], user_id=request.user.id)
                for category in data['categories']:
                    category_object, _ = Category.objects.get_or_create(id=category['id'], name=category['name'])
                    category_object.shops.add(shop.id)
                    category_object.save()
                ProductInfo.objects.filter(shop_id=shop.id).delete()
                for item in data['goods']:
                    product, _ = Product.objects.get_or_create(name=item['name'], category_id=item['category'])

                    product_info = ProductInfo.objects.create(product_id=product.id,
                                                              external_id=item['id'],
                                                              model=item['model'],
                                                              price=item['price'],
                                                              price_rrc=item['price_rrc'],
                                                              quantity=item['quantity'],
                                                              shop_id=shop.id)
                    for name, value in item['parameters'].items():
                        parameter_object, _ = Parameter.objects.get_or_create(name=name)
                        ProductParameter.objects.create(product_info_id=product_info.id,
                                                        parameter_id=parameter_object.id,
                                                        value=value)

                return JsonResponse({'Status': True})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})




class PartnerState(APIView):
    """
       A class for managing partner state.

       Methods:
       - get: Retrieve the state of the partner.

       Attributes:
       - None
       """
    # получить текущий статус
    def get(self, request, *args, **kwargs):
        """
               Retrieve the state of the partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the state of the partner.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)

        shop = request.user.shop
        serializer = ShopSerializer(shop)
        return Response(serializer.data)

    # изменить текущий статус
    def post(self, request, *args, **kwargs):
        """
               Update the state of a partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

        if request.user.type != 'shop':
            return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
        state = request.data.get('state')
        if state:
            try:
                Shop.objects.filter(user_id=request.user.id).update(state=strtobool(state))
                return JsonResponse({'Status': True})
            except ValueError as error:
                return JsonResponse({'Status': False, 'Errors': str(error)})

        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

        

class PartnerOrders(APIView):
     
    """
    Класс для получения заказов поставщиками
     Methods:
    - get: Retrieve the orders associated with the authenticated partner.

    Attributes:
    - None
    """
    def get(self, request, *args, **kwargs):
         """
               Retrieve the orders associated with the authenticated partner.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the orders associated with the partner.
               """
         
         if not request.user.is_authenticated:
             return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
         
         if request.user.type!='shop':
             return JsonResponse({'Status': False, 'Error': 'Только для магазинов'}, status=403)
         
         order = Order.objects.filter(
            ordered_items__product_info__shop__user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()
         
         serializer = OrderSerializer(order, many=True)
         return Response(serializer.data)


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

        # Получаем контакты пользователя, если они уже существуют
        contact = Contact.objects.filter(user=user).first()

        # Если контакты не найдены, создаем новый экземпляр Contact
        if not contact:
            contact = Contact(user=user)

        data = request.data.copy()
        serializer = ContactSerializer(contact, data=data, partial=True)  # partial=True позволяет обновлять частичные данные
        if serializer.is_valid():
            serializer.save()
            return Response({'Status': True}, status=status.HTTP_200_OK)
        return Response({'Status': False, 'Errors': serializer.errors}, status=status.HTTP_400_BAD_REQUEST)



    def put(self, request, user_id, *args, **kwargs):
        try:
            # Получаем контакт пользователя по user_id
            contact = Contact.objects.get(user_id=user_id)
        except Contact.DoesNotExist:
            # Если контакт не существует, создаем новый
            contact = Contact(user_id=user_id)

        # Сериализуем данные запроса
        serializer = ContactSerializer(contact, data=request.data, partial=True)
        if serializer.is_valid():
            # Сохраняем обновленные данные
            serializer.save()
            return Response(serializer.data, status=status.HTTP_200_OK)
        else:
            # Возвращаем ошибку валидации
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


    def delete(self, request, user_id, *args, **kwargs):
        contact = Contact.objects.filter(user_id=user_id).first()
        if contact:
            contact.delete()
            return Response({'Status': True}, status=status.HTTP_204_NO_CONTENT)
        return Response({'Status': False, 'Errors': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)


    def patch(self, request, user_id, *args, **kwargs):
        try:
            contact = Contact.objects.get(user_id=user_id)
        except Contact.DoesNotExist:
            return Response({'detail': 'Contact not found'}, status=status.HTTP_404_NOT_FOUND)

        data = request.data.copy()
        # Удаляем поля, переданные в запросе, устанавливая их значения в None
        for field in data:
            if data[field] is None:
                data[field] = None

        serializer = ContactSerializer(contact, data=data, partial=True)
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

    def get(self, request, *args, **kwargs):

        """
               Retrieve the details of user orders.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the details of the order.
               """
        
        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        
        order = Order.objects.filter(
            user_id=request.user.id).exclude(state='basket').prefetch_related(
            'ordered_items__product_info__product__category',
            'ordered_items__product_info__product_parameters__parameter').select_related('contact').annotate(
            total_sum=Sum(F('ordered_items__quantity') * F('ordered_items__product_info__price'))).distinct()

        serializer = OrderSerializer(order, many=True)
        return Response(serializer.data)
    
    # разместить заказ из корзины

    def post(self, request, *args, **kwargs):

        """
               Put an order and send a notification.

               Args:
               - request (Request): The Django request object.

               Returns:
               - JsonResponse: The response indicating the status of the operation and any errors.
               """

        if not request.user.is_authenticated:
            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
        if {'id', 'contact'}.issubset(request.data):
            if request.data['id'].isdigit():
                try:
                    is_updated = Order.objects.filter(
                        user_id=request.user.id, id=request.data['id']).update(
                        contact_id=request.data['contact'],
                        state='new')
                except IntegrityError as error:
                    print(error)
                    return JsonResponse({'Status': False, 'Errors': 'Неправильно указаны аргументы'})
                else:
                    if is_updated:
                        new_order.send(sender=self.__class__, user_id=request.user.id)
                        return JsonResponse({'Status': True})
                    
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})




class UserListView(APIView):
    def get(self, request):
        try:
            users = User.objects.all()
            serializer = UserSerializer(users, many=True)
            return Response(serializer.data)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)