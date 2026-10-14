from django.urls import include, path

urlpatterns = [path('api/v1/', include('api.urls'))]
handler404 = 'api.controllers.not_found'
handler500 = 'api.controllers.server_error'
