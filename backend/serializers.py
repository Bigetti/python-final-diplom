from rest_framework import serializers
import os


from backend.models import User, Category, Shop, ProductInfo, Product, ProductParameter, OrderItem, Order, Contact



class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = ['id', 'user', 'city', 'street', 'house', 'structure', 'building', 'apartment', 'phone_number']
        read_only_fields = ('id',) 


class PriceListUploadSerializer(serializers.Serializer):

    filePath = serializers.CharField(max_length=2000, required=True)

    def validate(self, attrs):
        filePath = attrs.get('filePath')

        if not filePath:
            raise serializers.ValidationError("The 'filePath' field is required.")

        # Здесь вы можете добавить проверку пути к файлу, например, чтобы убедиться, что файл существует
        if not os.path.exists(filePath):
            raise serializers.ValidationError("The file does not exist.")
        
        # Добавляем отладочные принты
        print("Received file path:", filePath)
        print("Does file exist?", os.path.exists(filePath))

        return attrs



class UserSerializer(serializers.ModelSerializer):

    contacts = ContactSerializer(read_only=True, many=True)

    class Meta:
        model = User
        fields = ('id', 'first_name', 'last_name', 'email', 'contacts')
        read_only_fields = ('id', )


class RegisterAccountSerializer(serializers.ModelSerializer):
  
    class Meta:
        model = User
        fields = ['id', 'email', 'password', 'first_name', 'last_name']
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user


class CategorySerializer(serializers.ModelSerializer):

    class Meta:
        model = Category
        fields = ('id', 'category_name',)
        read_only_fields = ('id',)


class ShopSerializer(serializers.ModelSerializer):

    class Meta:
        model = Shop
        fields = ('id', 'company_name', 'state',)
        read_only_fields = ('id',)



class ProductSerializer(serializers.ModelSerializer):

    class Meta:
        model = Product
        fields = ('product_name', 'category',)





class ProductParameterSerializer(serializers.ModelSerializer):
    parameter = serializers.StringRelatedField()

    class Meta:
        model = ProductParameter
        fields = ('parameter', 'value')



class ProductInfoSerializer(serializers.ModelSerializer):

    product = ProductSerializer(read_only=True)
    product_parameters = ProductParameterSerializer(read_only=True, many=True)

    class Meta:
        model = ProductInfo
        fields = ('id', 'product', 'shop', 'external_id', 'model', 'price', 'price_rrc', 'quantity', 'product_parameters')
        read_only_fields = ('id',)



class OrderItemCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ('id', 'order', 'product_info', 'quantity')
        read_only_fields = ('id',)
        extra_kwargs = {
            'order': {'write_only': True}
        }

    def create(self, validated_data):
        # Создаем элемент заказа
        return OrderItem.objects.create(**validated_data)
    


class OrderItemSerializer(serializers.ModelSerializer):
    product_info = ProductInfoSerializer(read_only=True)

    class Meta:
        model = OrderItem
        fields = ('id', 'order', 'product_info', 'quantity', 'price')
        read_only_fields = ('id',)

    def create(self, validated_data):
        # Убедитесь, что цена продукта указана
        product_info = validated_data.get('product_info')
        if product_info:
            validated_data['price'] = product_info.price  # Устанавливаем цену продукта
        return super().create(validated_data)
    

class OrderSerializer(serializers.ModelSerializer):
    ordered_items = OrderItemSerializer(many=True)
    contact = ContactSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ('id', 'ordered_items', 'status', 'contact')
        read_only_fields = ('id',)

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        # Вычисляем общую сумму заказа
        total_sum = sum(item.get_total_price() for item in instance.ordered_items.all())
        representation['total_sum'] = total_sum
        return representation