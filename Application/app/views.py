from django.shortcuts import render
from django.views.generic import TemplateView
from django.shortcuts import render, redirect, get_object_or_404
from .models import Inventory, Sale, BadOrder
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.views.decorators.http import require_http_methods
from .models import Expense
from .forms import ExpenseForm, SignupForm
from .models import Profile
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout

class HomePageView(TemplateView):
    template_name = 'app/home.html'

class  SalesPageView(TemplateView):
    template_name = 'app/sales.html'

def sales_page(request):
    return render(request, 'app/sales.html')

def get_sales_data(request):
    sales = list(Sale.objects.values())
    return JsonResponse(sales, safe=False)

def get_bad_orders_data(request):
    bad_orders = list(BadOrder.objects.values())
    return JsonResponse(bad_orders, safe=False)

@csrf_exempt
@require_http_methods(["POST"])
def add_sale(request):
    data = json.loads(request.body)
    sale = Sale.objects.create(
        product_name=data["product_name"],
        quantity=data["quantity"],
        price=data["price"],
        date=data["date"]
    )
    try:
        inventory_item = Inventory.objects.get(product_name=data["product_name"])
        inventory_item.stock = max(0, inventory_item.stock - data["quantity"])
        inventory_item.save()
    except Inventory.DoesNotExist:
        pass  
    return JsonResponse({"id": sale.id})

@csrf_exempt
def add_bad_order(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            bad_order = BadOrder.objects.create(
                transaction_id=data['transaction_id'],
                product_name=data['product_name'],
                quantity=data['quantity'],
                price=data['price'],
                reason=data['reason'],
                date=data['date']
            )
            return JsonResponse({'success': True, 'id': bad_order.id})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
@require_http_methods(["POST"])
def update_sale(request, pk):
    data = json.loads(request.body)
    sale = get_object_or_404(Sale, pk=pk)
    for field in ['product_name', 'quantity', 'price', 'date']:
        setattr(sale, field, data[field])
    sale.save()
    return JsonResponse({"status": "updated"})

@csrf_exempt
@require_http_methods(["POST"])
def update_bad_order(request, pk):
    data = json.loads(request.body)
    bo = get_object_or_404(BadOrder, pk=pk)
    for field in ['transaction_id', 'product_name', 'quantity', 'price', 'reason', 'date']:
        setattr(bo, field, data[field])
    bo.save()
    return JsonResponse({"status": "updated"})

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_sale(request, pk):
    sale = get_object_or_404(Sale, pk=pk)
    sale.delete()
    return JsonResponse({"status": "deleted"})

@csrf_exempt
@require_http_methods(["DELETE"])
def delete_bad_order(request, pk):
    bo = get_object_or_404(BadOrder, pk=pk)
    bo.delete()
    return JsonResponse({"status": "deleted"})

class  InventoryPageView(TemplateView):
    template_name = 'app/inventory.html'

def inventory_page(request):
    return render(request, 'app/inventory.html')

def get_inventory(request):
    inventory = list(Inventory.objects.values())
    return JsonResponse(inventory, safe=False)

@csrf_exempt
def inventory_get(request):
    """
    GET /inventory/get/
    Returns a list of all inventory products as JSON.
    """
    if request.method == 'GET':
        items = list(Inventory.objects.values('id', 'product_name', 'stock', 'price'))
        return JsonResponse(items, safe=False)

@csrf_exempt
def inventory_add(request):
    """
    POST /inventory/add/
    Adds a new product to inventory.
    Expects JSON: { "product_name": str, "stock": int, "price": float }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            # Validate required fields
            if not all(k in data for k in ('product_name', 'stock', 'price')):
                return JsonResponse({'error': 'Missing required fields.'}, status=400)
            # Validate types
            product_name = str(data['product_name']).strip()
            try:
                stock = int(data['stock'])
                price = float(data['price'])
            except Exception:
                return JsonResponse({'error': 'Stock must be integer and price must be a number.'}, status=400)
            if not product_name:
                return JsonResponse({'error': 'Product name cannot be empty.'}, status=400)
            item = Inventory.objects.create(
                product_name=product_name,
                stock=stock,
                price=price
            )
            return JsonResponse({'id': item.id}, status=201)
        except Exception as e:
            print("Error adding product:", e)
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def update_inventory(request, pk):
    """
    POST /inventory/update/<pk>/
    Updates an existing product.
    Expects JSON: { "product_name": str, "stock": int, "price": float }
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item = get_object_or_404(Inventory, pk=pk)
            item.product_name = data.get('product_name', item.product_name)
            item.stock = data.get('stock', item.stock)
            item.price = data.get('price', item.price)
            item.save()
            return JsonResponse({'status': 'updated'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def delete_inventory(request, pk):
    """
    POST /inventory/delete/<pk>/
    Deletes a product from inventory.
    """
    if request.method == 'POST':
        try:
            item = get_object_or_404(Inventory, pk=pk)
            item.delete()
            return JsonResponse({'status': 'deleted'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

class  ExpensesPageView(TemplateView):
    template_name = 'app/expenses.html'

def expenses(request):
    all_expenses = Expense.objects.all().order_by('-date')
    if request.method == 'POST':
        form = ExpenseForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('expenses')
    else:
        form = ExpenseForm()
    return render(request, 'app/expenses.html', {'form': form, 'expenses': all_expenses})

def delete_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    expense.delete()
    return redirect('expenses')

def update_expense(request, pk):
    expense = get_object_or_404(Expense, pk=pk)
    if request.method == 'POST':
        form = ExpenseForm(request.POST, instance=expense)
        if form.is_valid():
            form.save()
            return redirect('expenses')
    else:
        form = ExpenseForm(instance=expense)
    return render(request, 'app/update_expense.html', {'form': form})

class  RecordPageView(TemplateView):
    template_name = 'app/record.html'

class SigninPageView(View):
    template_name = 'registration/signin.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')
        user = authenticate(request, username=username, password=password)
        if user is not None:
            if hasattr(user, 'profile') and user.profile.role == role:
                login(request, user)
                if role == 'admin':
                    return redirect('home')
                else:
                    return redirect('dash')
            else:
                messages.error(request, "Role does not match your account.")
        else:
            messages.error(request, "Invalid username or password.")
        return render(request, self.template_name)

class SignupPageView(View):
    def get(self, request):
        form = SignupForm()
        return render(request, 'registration/signup.html', {'form': form})

    def post(self, request):
        full_name = request.POST.get('full_name', '')
        username = request.POST.get('username', '')
        password = request.POST.get('password', '')
        role = request.POST.get('role', 'user')
        names = full_name.strip().split(' ', 1)
        first_name = names[0]
        last_name = names[1] if len(names) > 1 else ''
        if User.objects.filter(username=username).exists():
            messages.error(request, "Username already exists.")
            return render(request, 'registration/signup.html')
        user = User.objects.create_user(
            username=username,
            password=password,
            first_name=first_name,
            last_name=last_name
        )
        Profile.objects.create(user=user, role=role)
        return redirect('signin')

class DashPageView(TemplateView):
    template_name = 'user/dash.html'

class  SalePageView(TemplateView):
    template_name = 'user/sale.html'

def signout(request):
    logout(request)
    messages.success(request, "You have been signed out successfully.")
    return redirect('signin')


