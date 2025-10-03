from django.urls import path
from .views import proxy_image, upload_image,  imagekit_auth, compress_image, upload_image_files, health_check

urlpatterns = [
    path('proxy-image/', proxy_image),
    path('upload-image/', upload_image),
    path('generate-imagekit-signature/', imagekit_auth, name='generate_imagekit_signature'), 
    path('compress-image/', compress_image, name='compress_image'),
    path("upload-imagekit-files/", upload_image_files, name="upload_imagekit_files"),
    path("health/", health_check, name="health-check"),
]
