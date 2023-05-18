from django.shortcuts import render, redirect, get_object_or_404
from store.models import Product, Variation
from carts.models import Cart, CartItem
from django.http import HttpResponse
from django.core.exceptions import ObjectDoesNotExist
from typing import ItemsView
from django.contrib.auth.decorators import login_required 

# Trong cái chorme phần cookie nó có session_key 
# Mỗi lần mình truy cập nó sẽ tự generate ra 1 session_key
def _cart_id(request):
    cart = request.session.session_key
    if not cart:
        cart = request.session.create()
    return cart


def add_cart(request, product_id):
    current_user = request.user # Lấy user để vào đúng cart
    product = Product.objects.get(id=product_id)

    # Trường hợp user đăng nhập
    if current_user.is_authenticated:
        # Lấy variation mà user add vào
        product_variation = []
        if request.method == 'POST':
            for item in request.POST:
                key = item
                value = request.POST[key]
                try:
                    variation = Variation.objects.get(product=product, variation_category__iexact=key, variation_value__iexact=value)
                    product_variation.append(variation)
                except:
                    pass
        
        # Check cart_item tồn tại?
        is_cart_item_exists = CartItem.objects.filter(product=product, user=current_user).exists()

        # Nếu cart_item tồn tại 
        # Check thêm product + variation tương ứng đã tồn tại chưa?
        # .id là nó tự generate theo thứ tự tăng dần, ko cần định nghĩa trong model
        if is_cart_item_exists:
            cart_item = CartItem.objects.filter(product=product, user=current_user) # check qua user, không phải _cart_id nữa
            ex_var_list = []
            id = []
            for item in cart_item:
                existing_variation = item.variations.all()
                ex_var_list.append(list(existing_variation))
                id.append(item.id) 

            # Nếu add product có varitaion cũ thì cart_item nó cộng thêm 1 thôi
            if product_variation in ex_var_list:
                index = ex_var_list.index(product_variation)
                item_id = id[index]
                item = CartItem.objects.get(product=product, id=item_id)
                item.quantity += 1
                item.save()

            # Còn nếu product đó nk mà variation mới thì tạo 1 cart_item khác
            else:
                item = CartItem.objects.create(product=product, quantity=1, user=current_user)
                if len(product_variation) > 0:
                    item.variations.clear()
                    item.variations.add(*product_variation)
                item.save()

        # Nếu cart_item ko tồn tại
        # Tạo thêm cart_item mới có cả variation tương ứng
        else:
            cart_item = CartItem.objects.create(
                product = product,
                quantity = 1,
                user = current_user,
            )
            if len(product_variation) > 0:
                cart_item.variations.clear()
                cart_item.variations.add(*product_variation)
            cart_item.save()
        return redirect('cart')
    
    # Trường hợp chưa đăng nhập
    else:
        product_variation = []
        # Vẫn là lấy variation
        if request.method == 'POST':
            for item in request.POST:
                key = item
                value = request.POST[key]

                try:
                    variation = Variation.objects.get(product=product, variation_category__iexact=key, variation_value__iexact=value)
                    product_variation.append(variation)
                except:
                    pass

        try:
            # Lấy cart dựa trên session_key
            # Nếu như đăng nhập rồi thì lấy user 
            cart = Cart.objects.get(cart_id=_cart_id(request)) 
        except Cart.DoesNotExist:
            cart = Cart.objects.create(
                cart_id = _cart_id(request)
            )
        cart.save()

        is_cart_item_exists = CartItem.objects.filter(product=product, cart=cart).exists()
        
        if is_cart_item_exists:
            cart_item = CartItem.objects.filter(product=product, cart=cart)
            # existing_variations -> database
            # current variation -> product_variation
            # item_id -> database
            ex_var_list = []
            id = []
            for item in cart_item:
                existing_variation = item.variations.all()
                ex_var_list.append(list(existing_variation))
                id.append(item.id)

            print(ex_var_list)

            # Nếu cái product đc add vào mà có variation cũ thì +1 thôi
            if product_variation in ex_var_list:
                index = ex_var_list.index(product_variation)
                item_id = id[index]
                item = CartItem.objects.get(product=product, id=item_id)
                item.quantity += 1
                item.save()
            # Nếu khác variation thì tạo cái mới
            else:
                item = CartItem.objects.create(product=product, quantity=1, cart=cart)
                if len(product_variation) > 0:
                    item.variations.clear()
                    item.variations.add(*product_variation)
                item.save()
        # Nếu product này chưa tồn tại thì tạo cái mới có cả variation tương ứng
        else:
            cart_item = CartItem.objects.create(
                product = product,
                quantity = 1,
                cart = cart,
            )
            if len(product_variation) > 0:
                cart_item.variations.clear()
                cart_item.variations.add(*product_variation)
            cart_item.save()
        return redirect('cart')


def remove_cart(request, product_id, cart_item_id):
    # Lấy product cần xóa
    product = get_object_or_404(Product, id=product_id)
    try:
        # Nếu đăng nhập r thì tìm cart_item theo user
        if request.user.is_authenticated:
            cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
        # Nếu chưa đăng nhập thì sẽ tìm theo session_key đc generate
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
        # Nếu sống lượng lớn hơn 1 thì trừ đi
        if cart_item.quantity > 1:
            cart_item.quantity -= 1
            cart_item.save()
        # Còn nếu bằng 1 trừ đi thì sẽ mất luôn cart_item
        else:
            cart_item.delete()
    except:
        pass
    return redirect('cart')


def remove_cart_item(request, product_id, cart_item_id):
    # Lấy cart_item cần xóa
    product = get_object_or_404(Product, id=product_id)
    # Nếu user đăng nhập r thì tìm cart_item theo user
    if request.user.is_authenticated:
        cart_item = CartItem.objects.get(product=product, user=request.user, id=cart_item_id)
    # Chưa đăng nhập thì tìm theo session_ley đc generate
    else:
        cart = Cart.objects.get(cart_id=_cart_id(request))
        cart_item = CartItem.objects.get(product=product, cart=cart, id=cart_item_id)
    cart_item.delete()
    return redirect('cart')


def cart(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        # Nếu đăng nhập thì sẽ tìm tất cả cart_item theo user
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        # Nếu chưa đăng nhập thì sẽ tìm tất cả cart_item theo cart (session_key)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (2 * total)/100
        grand_total = total + tax
    except ObjectDoesNotExist:
        pass 

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax'       : tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/cart.html', context)


@login_required(login_url='login')
def checkout(request, total=0, quantity=0, cart_items=None):
    try:
        tax = 0
        grand_total = 0
        if request.user.is_authenticated:
            cart_items = CartItem.objects.filter(user=request.user, is_active=True)
        else:
            cart = Cart.objects.get(cart_id=_cart_id(request))
            cart_items = CartItem.objects.filter(cart=cart, is_active=True)
        for cart_item in cart_items:
            total += (cart_item.product.price * cart_item.quantity)
            quantity += cart_item.quantity
        tax = (2 * total)/100
        grand_total = total + tax
    except ObjectDoesNotExist:
        pass 

    context = {
        'total': total,
        'quantity': quantity,
        'cart_items': cart_items,
        'tax'       : tax,
        'grand_total': grand_total,
    }
    return render(request, 'store/checkout.html', context)