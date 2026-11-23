from django.urls import path

from .views import catalog, content, hub, members, orders

app_name = "team"

urlpatterns = [
    path("", hub.hub, name="hub"),
    # Wines
    path("wines/", catalog.wine_list, name="wines"),
    path("wines/new/", catalog.WineCreateView.as_view(), name="wine_add"),
    path("wines/<int:pk>/edit/", catalog.WineUpdateView.as_view(), name="wine_edit"),
    path("wines/<int:pk>/delete/", catalog.WineDeleteView.as_view(), name="wine_delete"),
    path("wines/<int:pk>/toggle/", catalog.wine_toggle, name="wine_toggle"),
    path("wines/<int:pk>/stock/", catalog.wine_stock, name="wine_stock"),
    # Wineries
    path("wineries/", catalog.winery_list, name="wineries"),
    path("wineries/new/", catalog.WineryCreateView.as_view(), name="winery_add"),
    path("wineries/<int:pk>/edit/", catalog.WineryUpdateView.as_view(), name="winery_edit"),
    path("wineries/<int:pk>/delete/", catalog.WineryDeleteView.as_view(), name="winery_delete"),
    # Regions
    path("regions/", catalog.region_list, name="regions"),
    path("regions/new/", catalog.RegionCreateView.as_view(), name="region_add"),
    path("regions/<int:pk>/edit/", catalog.RegionUpdateView.as_view(), name="region_edit"),
    path("regions/<int:pk>/delete/", catalog.RegionDeleteView.as_view(), name="region_delete"),
    # Grapes
    path("grapes/", catalog.grape_list, name="grapes"),
    path("grapes/new/", catalog.GrapeCreateView.as_view(), name="grape_add"),
    path("grapes/<int:pk>/edit/", catalog.GrapeUpdateView.as_view(), name="grape_edit"),
    path("grapes/<int:pk>/delete/", catalog.GrapeDeleteView.as_view(), name="grape_delete"),
    # Orders
    path("orders/", orders.order_list, name="orders"),
    path("orders/packing-list.csv", orders.packing_list, name="packing_list"),
    path("orders/<str:number>/", orders.order_detail, name="order_detail"),
    path("orders/<str:number>/ship/", orders.order_ship, name="order_ship"),
    path("orders/<str:number>/delivered/", orders.order_delivered, name="order_delivered"),
    path("orders/<str:number>/cancel/", orders.order_cancel, name="order_cancel"),
    path("orders/<str:number>/note/", orders.order_note, name="order_note"),
    # Reviews
    path("reviews/", content.review_list, name="reviews"),
    path("reviews/<int:pk>/toggle/", content.review_toggle, name="review_toggle"),
    path("reviews/<int:pk>/delete/", content.ReviewDeleteView.as_view(), name="review_delete"),
    # Newsletter
    path("newsletter/", content.subscriber_list, name="subscribers"),
    path("newsletter/export.csv", content.subscriber_export, name="subscriber_export"),
    path("newsletter/<int:pk>/delete/", content.SubscriberDeleteView.as_view(), name="subscriber_delete"),
    # Legal pages
    path("pages/", content.page_list, name="pages"),
    path("pages/new/", content.PageCreateView.as_view(), name="page_add"),
    path("pages/<int:pk>/edit/", content.PageUpdateView.as_view(), name="page_edit"),
    path("pages/<int:pk>/delete/", content.PageDeleteView.as_view(), name="page_delete"),
    # Studio & team
    path("studio/", content.studio, name="studio"),
    path("members/", members.member_list, name="members"),
    path("members/<int:pk>/", members.member_edit, name="member_edit"),
]
