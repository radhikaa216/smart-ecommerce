from django.urls import path

from . import views


urlpatterns = [
    path("dashboard/", views.dashboard, name="dashboard"),
    path("reports/sales.csv", views.sales_csv, name="sales_csv"),
    path("reports/sales.pdf", views.sales_pdf, name="sales_pdf"),
]
