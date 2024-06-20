from django.urls import path
from django_rest_passwordreset.views import reset_password_request_token, reset_password_confirm

from django.views import View
from django.http import HttpResponse

from backend.views import RegisterAccount, LoginAccount, CategoryView, ShopView, ProductInfoView, BasketView, \
    AccountDetails, UserOrdersView, ContactView, OrderView, PartnerState, PartnerOrders, ConfirmAccount, UserListView, CustomPasswordResetView,PriceListUploadView, CustomPasswordResetConfirmView



app_name = 'backend'

urlpatterns = [
    path('partner/update', PriceListUploadView.as_view(), name='partner-update'),
    path('partner/state', PartnerState.as_view(), name='partner-state'),
    path('partner/orders/<int:shop_id>', PartnerOrders.as_view(), name='partner-orders'),
    path('user/register', RegisterAccount.as_view(), name='user-register'),
    path('user/register/confirm', ConfirmAccount.as_view(), name='user-register-confirm'),
    path('user/<int:user_id>/details', AccountDetails.as_view(), name='user-details'),
    path('user/contact', ContactView.as_view(), name='user-contact'),
    path('user/contact/<int:user_id>', ContactView.as_view(), name='contact-detail'),
    path('user/login', LoginAccount.as_view(), name='user-login'),
    path('user/password_reset', CustomPasswordResetView.as_view(), name='password-reset'),
    path('user/password_reset/confirm', CustomPasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    path('categories', CategoryView.as_view(), name='categories'),
    path('shops', ShopView.as_view(), name='shops'),
    path('products', ProductInfoView.as_view(), name='products'),
    path('basket', BasketView.as_view(), name='basket'),
    path('basket/user/<int:user_id>', BasketView.as_view(), name='basket-user'),
    path('ordermakebyuser/<int:user_id>', OrderView.as_view(), name='order'),
    path('orders/<int:user_id>/', OrderView.as_view(), name='user_orders'),
    path('users', UserListView.as_view(), name='user-list')

]