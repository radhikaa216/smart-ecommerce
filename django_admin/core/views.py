import csv
from io import BytesIO

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Count, DateField, F, Func, Sum
from django.http import HttpResponse
from django.shortcuts import render
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

from .models import Customer, Order, OrderItem, Product


def analytics_context():
    paid = Order.objects.filter(payment_status="paid")
    revenue = paid.aggregate(value=Sum("total"))["value"] or 0
    top_products = list(
        OrderItem.objects.filter(order__payment_status="paid")
        .values("product_name")
        .annotate(quantity=Sum("quantity"), revenue=Sum("line_total"))
        .order_by("-quantity")[:5]
    )
    # Use MySQL DATE() directly. Django's TruncDate performs timezone
    # conversion first; that returns NULL on local MySQL installations whose
    # timezone tables have not been loaded.
    revenue_trend = [
        row
        for row in paid.annotate(
            day=Func(F("created_at"), function="DATE", output_field=DateField())
        )
        .values("day")
        .annotate(revenue=Sum("total"), orders=Count("id"))
        .order_by("day")[:30]
        if row["day"] is not None
    ]
    return {
        "total_revenue": revenue,
        "total_orders": Order.objects.count(),
        "paid_orders": paid.count(),
        "customers": Customer.objects.filter(role="customer").count(),
        "low_stock": Product.objects.filter(is_active=True, stock__lte=F("low_stock_threshold")).order_by("stock")[:10],
        "top_products": top_products,
        "revenue_trend": revenue_trend,
        "chart_labels": [row["day"].isoformat() for row in revenue_trend],
        "chart_values": [float(row["revenue"]) for row in revenue_trend],
    }


@staff_member_required
def dashboard(request):
    return render(request, "dashboard.html", analytics_context())


@staff_member_required
def sales_csv(request):
    response = HttpResponse(content_type="text/csv", headers={"Content-Disposition": 'attachment; filename="sales-report.csv"'})
    writer = csv.writer(response)
    writer.writerow(["Order", "Customer", "Created", "Payment", "Status", "Currency", "Total"])
    for order in Order.objects.select_related("customer").order_by("-created_at"):
        writer.writerow([order.order_number, order.customer.email, order.created_at.isoformat(), order.payment_status, order.order_status, order.currency, order.total])
    return response


@staff_member_required
def sales_pdf(request):
    buffer = BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 50
    pdf.setFont("Helvetica-Bold", 16)
    pdf.drawString(40, y, "Smart Ecommerce Sales Report")
    y -= 30
    pdf.setFont("Helvetica", 9)
    for order in Order.objects.select_related("customer").order_by("-created_at")[:100]:
        pdf.drawString(40, y, f"{order.order_number}  {order.customer.email[:28]:28}  {order.payment_status:10}  {order.currency} {order.total}")
        y -= 15
        if y < 40:
            pdf.showPage()
            pdf.setFont("Helvetica", 9)
            y = height - 40
    pdf.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf", headers={"Content-Disposition": 'attachment; filename="sales-report.pdf"'})
