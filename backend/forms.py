# forms.py
from django import forms
from .models import OrderItem, ProductInfo

class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['order', 'product_info', 'quantity', 'price']

    def __init__(self, *args, **kwargs):
        super(OrderItemForm, self).__init__(*args, **kwargs)
        self.fields['product_info'].label_from_instance = lambda obj: f"{obj.product.product_name}"

        