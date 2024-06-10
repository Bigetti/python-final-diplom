from django.contrib import admin
from django.contrib.auth.admin import UserAdmin


from django import forms



from .models import User, Shop, Category, Product, ProductInfo, Parameter, ProductParameter, Order, OrderItem, Contact, ConfirmEmailToken



@admin.register(User)
class CustomUserAdmin(UserAdmin):
    """
    Панель управления пользователями
    """
    model = User
    
    fieldsets = (
        (None, {'fields': ('email', 'password', 'type', 'token')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'company', 'position')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    list_display = ('id', 'email', 'first_name', 'last_name', 'is_staff', 'token') # noqa: impo
    ordering = ('email',)  # Указываем поле для сортировки
    search_fields = ('email',)
    actions = ['delete_selected'] 
    

def token(self, obj):
        # Получаем последний токен пользователя
        token = ConfirmEmailToken.objects.filter(user=obj).last()
        return token.token if token else None
    



@admin.register(Shop)
class ShopAdmin(admin.ModelAdmin):
    """
    Панель управления магазинами
    """
    list_display = ('company_name', 'state')


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Панель управления категориями
    """
    list_display = ('category_name',)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """
    Панель управления продуктами
    """
    list_display = ('product_name', 'category')


@admin.register(ProductInfo)
class ProductInfoAdmin(admin.ModelAdmin):
    """
    Панель управления информацией о продуктах
    """
    list_display = ('product', 'model', 'shop', 'quantity', 'price', 'price_rrc')


@admin.register(Parameter)
class ParameterAdmin(admin.ModelAdmin):
    """
    Панель управления параметрами
    """
    list_display = ('parameter_name',)


@admin.register(ProductParameter)
class ProductParameterAdmin(admin.ModelAdmin):
    """
    Панель управления параметрами
    """
    list_display = ('product_info', 'parameter', 'value')



class OrderItemInline(admin.TabularInline):
    model = OrderItem




@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    """
    Панель управления заказами
    """
    list_display = ('user', 'status', 'created_at', 'updated_at')
    list_filter = ('status', 'created_at')
    search_fields = ('user__email', 'status')
    

    inlines = [OrderItemInline]



@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    """
    Панель управления элементами заказа
    """
    list_display = ('order', 'product_info', 'quantity', 'price')


@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    """
    Панель управления контактами
    """
    list_display = ('user', 'city', 'street', 'house')


@admin.register(ConfirmEmailToken)
class ConfirmEmailTokenAdmin(admin.ModelAdmin):
    """
    Панель управления токенами подтверждения электронной почты
    """
    list_display = ('id', 'user', 'token', 'created_at')


