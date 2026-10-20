"""Stateless local API: no Django users, sessions or application database."""
import os
import secrets
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')
SECRET_KEY = os.getenv('DJANGO_SECRET_KEY') or secrets.token_urlsafe(64)
DEBUG = os.getenv('DJANGO_DEBUG', 'false').lower() == 'true'
ALLOWED_HOSTS = [h.strip() for h in os.getenv('DJANGO_ALLOWED_HOSTS','localhost,127.0.0.1').split(',') if h.strip()]
ROOT_URLCONF = 'ti_api.urls'
WSGI_APPLICATION = 'ti_api.wsgi.application'
ASGI_APPLICATION = 'ti_api.asgi.application'
INSTALLED_APPS = ['api.apps.RagApiConfig', 'drf_spectacular_sidecar']
TEMPLATES = [{'BACKEND':'django.template.backends.django.DjangoTemplates',
              'APP_DIRS':True, 'OPTIONS':{}}]
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]
DATABASES = {}
LANGUAGE_CODE = 'es-co'
TIME_ZONE = 'America/Bogota'
USE_TZ = True
APPEND_SLASH = False
DATA_UPLOAD_MAX_MEMORY_SIZE = 16 * 1024
RAG_API_TOKEN = os.getenv('DJANGO_API_TOKEN','')
RAG_INDEX_PATH = BASE_DIR / 'data/indexes/sections'
# Keep request bodies and Authorization out of application logs.
LOGGING = {'version':1,'disable_existing_loggers':False,
           'handlers':{'console':{'class':'logging.StreamHandler'}},
           'loggers':{'api':{'handlers':['console'],'level':'INFO','propagate':False}}}
