from django.shortcuts import render, get_object_or_404, reverse, redirect
from .models import Product, OrderDetail
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
# from django.urls import reverse
import stripe, json
from django.http import JsonResponse, HttpResponseNotFound
from .forms import ProductForm, UserRegisterForm
from django.contrib.auth.decorators import login_required


# Create your views here.
def index(request):
    products = Product.objects.all()
    return render(request,'myapp/index.html',{'products':products})


def detail(request,id):
    product = Product.objects.get(id=id)
    stripe_publishable_key = settings.STRIPE_PUBLISHABLE_KEY
    
    return render(request,'myapp/detail.html',
                  {'product':product,
                   'stripe_publishable_key':stripe_publishable_key})




# view for stripe checkout
@login_required
@csrf_exempt
def create_checkout_session(request, id):
    # get the request data
    request_data = json.loads(request.body)
    # print(request_data)

    # access the product data
    product = Product.objects.get(id=id)
    stripe.api_key = settings.STRIPE_SECRET_KEY

    # create a checkout session
    checkout_session = stripe.checkout.Session.create(
        customer_email=request_data['email'].strip(),
        payment_method_types=['card'],
        line_items=[
            {
                'price_data': {
                    'currency': 'usd',
                    'product_data': {
                        'name': product.name,
                    },
                    'unit_amount': int(product.price * 100)
                },
                'quantity': 1,
            }
        ],
        mode='payment',
        # success & cancel page URLs
        success_url=request.build_absolute_uri(reverse('success')) +
        "?session_id={CHECKOUT_SESSION_ID}",
        cancel_url=request.build_absolute_uri(reverse('failed')),
    )

    print('CHECKOUT SESSION CREATED')
    print(checkout_session)

    # creating order after checkout
    order = OrderDetail()
    order.customer_email = request_data['email']
    order.product = product
    order.amount = product.price
    # Note: the checkout_session.payment_intent = 'null'. SO session_id is stored
    # for retrieving the order in the success view. And once the payment is SUCCESS,
    # the paymnet_intent is stored in the session, which can be saved to the order
    order.stripe_checkout_session_id = checkout_session.id
    order.save()

    # returning a JSON response
    return JsonResponse({'sessionId': checkout_session.id})



@login_required
def payment_success_view(request):
    session_id = request.GET.get('session_id')
    if session_id is None:
        return HttpResponseNotFound()

    stripe.api_key = settings.STRIPE_SECRET_KEY

    session = stripe.checkout.Session.retrieve(session_id)

    order = get_object_or_404(OrderDetail, stripe_checkout_session_id=session_id)
    order.stripe_payment_intent = session.payment_intent
    order.has_paid = True
    order.save()

    return render(request, 'myapp/payment_success.html', {'order': order})


@login_required
def payment_failed_view(request):
    return render(request,'myapp/payment_failed.html')



@login_required
def create_product(request):

    if request.method=="POST":
        product_form = ProductForm(request.POST,request.FILES)
        if product_form.is_valid():
            new_product = product_form.save(commit=False)
            new_product.seller = request.user
            new_product.save()
            return redirect('index')

    product_form = ProductForm()
    return render(request,'myapp/create_product.html',{'product_form':product_form})



@login_required
def edit_product(request,id):
    product = Product.objects.get(id=id)
    if product.seller != request.user:
        return redirect('invalid')
    product_form = ProductForm(request.POST or None,request.FILES or None, instance=product)
    if request.method == "POST":
        if product_form.is_valid():
            product_form.save()
            return redirect('index')
    return render(request,'myapp/edit_product.html',{'product_form':product_form,'product':product})



@login_required
def delete_product(request,id):
    product = Product.objects.get(id=id)
    if product.seller != request.user:
        return redirect('invalid')
    if request.method=='POST':
        product.delete()
        return redirect('index')
    return render(request,'myapp/delete.html')



@login_required
def dashboard(request):
    products = Product.objects.filter(seller=request.user)
    return render(request,'myapp/dashboard.html',{'products':products})


def register(request):
    user_form = UserRegisterForm(request.POST or None)
    if request.method=="POST":
        if user_form.is_valid():
            new_user = user_form.save(commit=False)
            new_user.set_password(user_form.cleaned_data['password'])
            new_user.save()
            return redirect('index')
    return render(request,'myapp/register.html',{'user_form':user_form})


def invalid(request):
    return render(request,'myapp/invalid.html')


def my_orders(request):
    orders = OrderDetail.objects.all()
    return render(request,'myapp/orders.html',{'orders':orders})