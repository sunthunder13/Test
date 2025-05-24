from django.shortcuts import render
from django.views.generic import TemplateView
from django.shortcuts import render, redirect, get_object_or_404
from .models import Inventory, Sale, BadOrder
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.views.decorators.http import require_http_methods, require_GET
from .models import Expense
from .forms import ExpenseForm, SignupForm
from .models import Profile
from django.contrib.auth.models import User
from django.shortcuts import render, redirect
from django.views import View
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.db.models import Sum, F
from django.db.models.functions import TruncDate
from datetime import datetime
from django.utils import timezone
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator

class HomePageView(TemplateView):
    template_name = 'app/home.html'

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'profile') or request.user.profile.role != 'admin':
            return HttpResponseForbidden("You do not have permission to access this page.")
        today = timezone.localdate()
        total_sales = Sale.objects.filter(date=today).aggregate(total=Sum('price'))['total'] or 0
        total_bad_orders = BadOrder.objects.filter(date=today).count()
        total_expenses = Expense.objects.filter(date=today).aggregate(total=Sum('amount'))['total'] or 0
        total_stock_quantity = Inventory.objects.filter(date=today).aggregate(total=Sum('stock'))['total'] or 0
        context = self.get_context_data(**kwargs)
        context['total_sales'] = total_sales
        context['total_bad_orders'] = total_bad_orders
        context['total_expenses'] = total_expenses
        context['total_stock_quantity'] = total_stock_quantity
        return self.render_to_response(context)

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
                product_name=data['product_name'],
                quantity=data['quantity'],
                price=data['price'],
                reason=data['reason'],
                date=data['date']
            )
            bad_order.transaction_id = f"BO-{bad_order.pk:06d}"
            bad_order.save()
            try:
                inventory_item = Inventory.objects.get(product_name=data["product_name"])
                inventory_item.stock = max(0, inventory_item.stock - data["quantity"])
                inventory_item.save()
            except Inventory.DoesNotExist:
                pass
            return JsonResponse({'success': True, 'id': bad_order.id, 'transaction_id': bad_order.transaction_id})
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
    if request.method == 'GET':
        items = list(Inventory.objects.values('id', 'product_name', 'stock', 'retail_price', 'price'))
        return JsonResponse(items, safe=False)

@csrf_exempt
def inventory_add(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            if not all(k in data for k in ('product_name', 'stock', 'retail_price', 'price', 'date')):
                return JsonResponse({'error': 'Missing required fields.'}, status=400)
            product_name = str(data['product_name']).strip()
            try:
                stock = int(data['stock'])
                retail_price = float(data['retail_price'])
                price = float(data['price'])
                date = data['date']
            except Exception:
                return JsonResponse({'error': 'Stock, retail price, price, and date must be valid.'}, status=400)
            if not product_name:
                return JsonResponse({'error': 'Product name cannot be empty.'}, status=400)
            item = Inventory.objects.create(
                product_name=product_name,
                stock=stock,
                retail_price=retail_price,
                price=price,
                date=date
            )
            return JsonResponse({'id': item.id}, status=201)
        except Exception as e:
            print("Error adding product:", e)
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def update_inventory(request, pk):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            item = get_object_or_404(Inventory, pk=pk)
            item.product_name = data.get('product_name', item.product_name)
            item.stock = data.get('stock', item.stock)
            item.retail_price = data.get('retail_price', item.retail_price)
            item.price = data.get('price', item.price)
            if 'date' in data:
                item.date = data['date']
            item.save()
            return JsonResponse({'status': 'updated'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=400)
    return JsonResponse({'error': 'Invalid method'}, status=405)

@csrf_exempt
def delete_inventory(request, pk):
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

@csrf_exempt
@require_GET
def get_expenses(request):
    expenses = list(Expense.objects.values())
    return JsonResponse(expenses, safe=False)

@csrf_exempt
@require_http_methods(["POST"])
def add_expense(request):
    try:
        data = json.loads(request.body)
        expense = Expense.objects.create(
            date=data['date'],
            description=data['description'],
            category=data['category'],
            amount=data['amount']
        )
        return JsonResponse({'id': expense.id}, status=201)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST"])
def update_expense_api(request, pk):
    try:
        data = json.loads(request.body)
        expense = get_object_or_404(Expense, pk=pk)
        expense.date = data.get('date', expense.date)
        expense.description = data.get('description', expense.description)
        expense.category = data.get('category', expense.category)
        expense.amount = data.get('amount', expense.amount)
        expense.save()
        return JsonResponse({'status': 'updated'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

@csrf_exempt
@require_http_methods(["POST", "DELETE"])
def delete_expense_api(request, pk):
    try:
        expense = get_object_or_404(Expense, pk=pk)
        expense.delete()
        return JsonResponse({'status': 'deleted'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)

class  RecordPageView(TemplateView):
    template_name = 'app/record.html'

    def get(self, request, *args, **kwargs):
        from_date = request.GET.get('from_date')
        to_date = request.GET.get('to_date')
        date_filter = {}
        if from_date:
            date_filter['date__gte'] = from_date
        if to_date:
            date_filter['date__lte'] = to_date
        sales_qs = Sale.objects.filter(**date_filter) if date_filter else Sale.objects.all()
        bad_orders_qs = BadOrder.objects.filter(**date_filter) if date_filter else BadOrder.objects.all()
        expenses_qs = Expense.objects.filter(**date_filter) if date_filter else Expense.objects.all()
        inventory_qs = Inventory.objects.filter(**date_filter) if date_filter else Inventory.objects.all()
        today = timezone.localdate()
        summary_sales = Sale.objects.filter(date=today).aggregate(total=Sum('price'))['total'] or 0
        summary_bad_orders = BadOrder.objects.filter(date=today).aggregate(total=Sum('price'))['total'] or 0
        summary_expenses = Expense.objects.filter(date=today).aggregate(total=Sum('amount'))['total'] or 0
        summary_inventory = Inventory.objects.filter(date=today).aggregate(
            total=Sum(F('stock') * F('retail_price'))
        )['total'] or 0
        summary_net_profit = summary_sales - summary_bad_orders - summary_expenses
        total_sales = sales_qs.aggregate(total=Sum('price'))['total'] or 0
        total_bad_orders_price = bad_orders_qs.aggregate(total=Sum('price'))['total'] or 0
        total_expenses = expenses_qs.aggregate(total=Sum('amount'))['total'] or 0
        inventory_total_value = inventory_qs.aggregate(
            total=Sum(F('stock') * F('retail_price'))
        )['total'] or 0
        net_profit = total_sales - total_bad_orders_price - total_expenses
        sales_by_date = (
            sales_qs.values('date')
            .annotate(total_sales=Sum('price'))
        )
        bad_orders_by_date = (
            bad_orders_qs.values('date')
            .annotate(total_bad_orders=Sum('price'))
        )
        expenses_by_date = (
            expenses_qs.values('date')
            .annotate(total_expenses=Sum('amount'))
        )
        all_dates = set()
        all_dates.update([s['date'] for s in sales_by_date])
        all_dates.update([b['date'] for b in bad_orders_by_date])
        all_dates.update([e['date'] for e in expenses_by_date])
        record_history = []
        for date in sorted(all_dates, reverse=True):
            sales = next((s['total_sales'] for s in sales_by_date if s['date'] == date), 0)
            bad_orders = next((b['total_bad_orders'] for b in bad_orders_by_date if b['date'] == date), 0)
            expenses = next((e['total_expenses'] for e in expenses_by_date if e['date'] == date), 0)
            net = sales - bad_orders - expenses
            record_history.append({
                'date': date,
                'total_sales': sales,
                'total_bad_orders': bad_orders,
                'total_expenses': expenses,
                'net_profit': net,
            })
        inventory_summary = [
            {
                'product_name': item.product_name,
                'stock': item.stock,
                'retail_price': item.retail_price,
                'total_value': item.stock * item.retail_price,
                'date': item.date
            }
            for item in inventory_qs
        ]
        context = self.get_context_data(**kwargs)
        context['total_sales'] = summary_sales
        context['total_bad_orders_price'] = summary_bad_orders
        context['total_expenses'] = summary_expenses
        context['inventory_total_value'] = summary_inventory
        context['net_profit'] = summary_net_profit
        context['record_history'] = record_history
        context['inventory_summary'] = inventory_summary
        context['from_date'] = from_date or ''
        context['to_date'] = to_date or ''
        return self.render_to_response(context)

class SigninPageView(View):
    template_name = 'registration/signin.html'

    def get(self, request):
        return render(request, self.template_name)

    def post(self, request):
        username = request.POST.get('username')
        password = request.POST.get('password')
        role = request.POST.get('role')
        user = authenticate(request, username=username, password=password)
        if user is not None and hasattr(user, 'profile'):
            if user.profile.role == role:
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

    def get(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
            return HttpResponseForbidden("You do not have permission to access this page.")
        today = timezone.localdate()
        total_sales = Sale.objects.filter(date=today).aggregate(total=Sum('price'))['total'] or 0
        total_bad_orders = BadOrder.objects.filter(date=today).count()
        total_expenses = Expense.objects.filter(date=today).aggregate(total=Sum('amount'))['total'] or 0
        total_stock_quantity = Inventory.objects.filter(date=today).aggregate(total=Sum('stock'))['total'] or 0
        context = self.get_context_data(**kwargs)
        context['total_sales'] = total_sales
        context['total_bad_orders'] = total_bad_orders
        context['total_expenses'] = total_expenses
        context['total_stock_quantity'] = total_stock_quantity
        return self.render_to_response(context)

class SalePageView(TemplateView):
    template_name = 'user/sale.html'

def signout(request):
    logout(request)
    messages.success(request, "You have been signed out successfully.")
    return redirect('signin')

# --- USER API ENDPOINTS FOR sale.html ---

from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from .models import Sale, BadOrder, Inventory

@login_required
def user_get_sales(request):
    # Only allow users with 'user' role
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({"error": "User does not have 'user' role."}, status=403)
    sales = list(Sale.objects.values())
    return JsonResponse(sales, safe=False)

@login_required
def user_get_bad_orders(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({"error": "User does not have 'user' role."}, status=403)
    bad_orders = list(BadOrder.objects.values())
    return JsonResponse(bad_orders, safe=False)

@csrf_exempt
@login_required
def user_add_sale(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({"error": "User does not have 'user' role."}, status=403)
    import json
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
@login_required
def user_add_bad_order(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid method"}, status=405)
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({"error": "User does not have 'user' role."}, status=403)
    import json
    try:
        data = json.loads(request.body)
        bad_order = BadOrder.objects.create(
            product_name=data['product_name'],
            quantity=data['quantity'],
            price=data['price'],
            reason=data['reason'],
            date=data['date']
        )
        bad_order.transaction_id = f"BO-{bad_order.pk:06d}"
        bad_order.save()
        try:
            inventory_item = Inventory.objects.get(product_name=data["product_name"])
            inventory_item.stock = max(0, inventory_item.stock - data["quantity"])
            inventory_item.save()
        except Inventory.DoesNotExist:
            pass
        return JsonResponse({'success': True, 'id': bad_order.id, 'transaction_id': bad_order.transaction_id})
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)}, status=400)

@csrf_exempt
@login_required
def user_delete_sale(request, pk):
    if request.method != "DELETE":
        return JsonResponse({"error": "Invalid method"}, status=405)
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({"error": "User does not have 'user' role."}, status=403)
    sale = get_object_or_404(Sale, pk=pk)
    sale.delete()
    return JsonResponse({"status": "deleted"})

@csrf_exempt
@login_required
def user_delete_bad_order(request, pk):
    if request.method != "DELETE":
        return JsonResponse({"error": "Invalid method"}, status=405)
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return JsonResponse({"error": "User does not have 'user' role."}, status=403)
    bo = get_object_or_404(BadOrder, pk=pk)
    bo.delete()
    return JsonResponse({"status": "deleted"})

@login_required
def user_inventory_get(request):
    if not hasattr(request.user, 'profile') or request.user.profile.role != 'user':
        return HttpResponseForbidden("You do not have permission to access this page.")
    items = list(Inventory.objects.values('id', 'product_name', 'stock', 'retail_price', 'price'))
    return JsonResponse(items, safe=False)

from django.views.decorators.http import require_GET

@require_GET
def get_all_products(request):
    items = list(Inventory.objects.values('id', 'product_name', 'stock', 'retail_price', 'price'))
    return JsonResponse(items, safe=False)



