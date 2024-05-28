from django.shortcuts import render
import yaml
from distutils.util import strtobool

from rest_framework.views import APIView
from rest_framework.response import Request
from rest_framework.response import Response
from django.contrib.auth import authenticate
from django.contrib.auth.password_validation import validate_password
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
from serializers import PriceListUploadSerializer, UserSerializer, CategorySerializer, ShopSerializer, ProductSerializer, ProductInfoSerializer, ProductParameterSerializer, OrderSerializer,
from .models import Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact, User



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
                error_array = []
                error_array.append(password_error)
                return JsonResponse({"status": "error", "errors": error_array}, status=status.HTTP_400_BAD_REQUEST)
            else:

                # проверяем данные для уникальности имени пользователя
                user_serializer = UserSerializer(data=request.data)
                if user_serializer.is_valid():
                    # сохраняем пользователя
                    user = user_serializer.save()
                    user.set_password(request.data['password'])
                    user.save()
                    return JsonResponse({"status": "success"}, status=status.HTTP_200_OK)
                else:
                    return JsonResponse({"status": "error", "errors": user_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
                
        return JsonResponse({"status": "error", "errors": "Не указаны все необходимые аргументы"}, status=status.HTTP_400_BAD_REQUEST)
    
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
        
          # Проверяем обязательные аргументы
        if {'email', 'token'}.issubset(request.data):

            token = ConfirmEmailToken.objects.filter(user__email=request.data['email'], token=request.data['token']).first()
            if token:
                token.user.is_active = True
                token.user.save()
                token.delete()
                return JsonResponse({"status": "success"}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({"status": "error", "errors": "Неверный токен"}, status=status.HTTP_400_BAD_REQUEST)
        return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
    


    class AccountDetails(APIView):
        """
        Класс для получения информации о пользователе
        """
        def get(self, request, *args, **kwargs):
            """
                Получает информацию о пользователе.

                Args:
                - request (Request): The Django request object.
                Returns:
                - JsonResponse: The response containing the user's information.
                """
            if not request.user.is_authenticated:
                return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
            
            serializer = UserSerializer(request.user)
            return JsonResponse(serializer.data, status=status.HTTP_200_OK)
        
        def post(self, request, *args, **kwargs):
            
            """
                Update the account details of the authenticated user.

                Args:
                - request (Request): The Django request object.

                Returns:
                - JsonResponse: The response indicating the status of the operation and any errors.
                """
            
            
            if not request.user.is_authenticated:
                return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
            # проверяем обязательные аргументы
            if not request.user.is_authenticated:
                return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)

            if {'email', 'first_name', 'last_name'}.issubset(request.data):
                # валидируем пароль 
                try:
                    validate_password(request.data['password'])
                except Exception as password_error:
                    error_array = []
                    error_array.append(password_error)
                    return JsonResponse({"status": "error", "errors": error_array}, status=status.HTTP_400_BAD_REQUEST)
                else:
                    request.user.set_password(request.data['password'])


            user_serializer = UserSerializer(request.user, data=request.data, partial=True)
            if user_serializer.is_valid():
                user_serializer.save()
                return JsonResponse({"status": "success"}, status=status.HTTP_200_OK)
            else:
                return JsonResponse({"status": "error", "errors": user_serializer.errors}, status=status.HTTP_400_BAD_REQUEST)
            

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
        """
       A class for managing contact information.

       Methods:
       - get: Retrieve the contact information of the authenticated user.
       - post: Create a new contact for the authenticated user.
       - put: Update the contact information of the authenticated user.
       - delete: Delete the contact of the authenticated user.

       Attributes:
       - None
       """
        
        def get(self, request, *args, **kwargs):
            """
               Retrieve the contact information of the authenticated user.

               Args:
               - request (Request): The Django request object.

               Returns:
               - Response: The response containing the contact information.
               """
            

            if not request.user.is_authenticated:
                return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
            
            contact = Contact.objects.filter(user_id=request.user.id)
            serializer = ContactSerializer(contact, many=True)
            return Response(serializer.data)


            # Создать новый контакт
        def post(self, request, *args, **kwargs):
               
            """
               Create a new contact for the authenticated user.
                Args:
                - request (Request): The Django request object.
                Returns: The Response indicating the status of the operation and any errors.
                """
            if not request.user.is_authenticated:
                            return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
            
            if {'city', 'address', 'phone'}.issubnet(request.data):
                request.data._mutable = True
                request.data.update({'user_id': request.user.id})
                serializer = ContactSerializer(data=request.data)

                if serializer.is_valid():
                    serializer.save()
                    return JsonResponse({'Status': True})
                else:
                    return JsonResponse({'Status': False, 'Errors': serializer.errors})

            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})
        

         # удалить контакт
        def delete(self, request, *args, **kwargs):
            
            """
               Delete the contact of the authenticated user.
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
                query = Q()
                objects_deleted = False
                for contact_id in items_list:
                    if contact_id.isdigit():
                        query = query | Q(user_id=request.user.id, id=contact_id)
                        objects_deleted = True


                if objects_deleted:
                    deleted_count = Contact.objects.filter(query).delete()[0]
                    return JsonResponse({'Status': True, 'Обновлено объектов': deleted_count})
                
            return JsonResponse({'Status': False, 'Errors': 'Не указаны все необходимые аргументы'})

        # редактировать контакт
        def put(self, request, *args, **kwargs):

            if not request.user.is_authenticated:
                """
                   Update the contact information of the authenticated user.

                   Args:
                   - request (Request): The Django request object.

                   Returns:
                   - JsonResponse: The response indicating the status of the operation and any errors.
                   """

                return JsonResponse({'Status': False, 'Error': 'Log in required'}, status=403)
                                    
            if 'id' in request.data:
                if request.data['id'].isdigit():
                    contact = Contact.objects.filter(id=request.data['id'], user_id=request.user.id).first()
                    print(contact)
                if contact:
                    serializer = ContactSerializer(contact, data=request.data, partial=True)
                    if serializer.is_valid():
                        serializer.save()
                        return JsonResponse({'Status': True})
                    else:
                        return JsonResponse({'Status': False, 'Errors': serializer.errors})
                        

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



