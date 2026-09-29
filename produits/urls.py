from django.urls import path

from produits import views

urlpatterns = [
    path("produits/", views.CatalogueView.as_view()),
    path("produits/creer/", views.ProduitCreateView.as_view()),
    path("produits/creer-rapide/", views.ProduitCreerRapideView.as_view()),
    path("produits/tous/", views.ProduitTousView.as_view()),
    path("produits/alertes-stock/", views.AlertesStockView.as_view()),
    path("produits/<int:produit_id>/", views.ProduitUpdateView.as_view()),
    path("produits/<int:produit_id>/qr/", views.QRCodeView.as_view()),
    path("produits/<int:produit_id>/barcode/", views.BarcodeView.as_view()),
    path("produits/<int:produit_id>/code-barre/", views.BarcodeView.as_view()),
    path("produits/<int:produit_id>/qrcode-pdf/", views.ProduitQrPdfView.as_view()),
    path("produits/<int:produit_id>/barcode-pdf/", views.ProduitQrPdfView.as_view()),
    path("produits/catalogue-sync/", views.CatalogueSyncView.as_view()),
]
