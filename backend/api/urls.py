from django.urls import path
from .controllers import HealthController,CategoriesController,SearchController,QueryController,OCRExtractController
from .documentation import schema, swagger, swagger_asset

urlpatterns = [
    path('docs/',swagger,name='swagger'),
    path('docs/assets/<str:filename>',swagger_asset,name='swagger-asset'),
    path('openapi.json',schema,name='openapi-schema'),
    path('health/',HealthController.as_view(),name='health'),
    path('categories/',CategoriesController.as_view(),name='categories'),
    path('rag/search/',SearchController.as_view(),name='rag-search'),
    path('rag/query/',QueryController.as_view(),name='rag-query'),
    path('ocr/extract/',OCRExtractController.as_view(),name='ocr-extract'),
]
