# api/views.py
import requests
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from imagekitio import ImageKit
import base64
import json
import tinify

# ImageKit config
imagekit = ImageKit(
    private_key="private_8wYbxoINX83O+QgkmJVErl8DRWA=",
    public_key="public_b1sQ/8elvKd9V/hGdmIbuNec55k=",
    url_endpoint="https://ik.imagekit.io/zakwan601"
)


# -----------------------
# Proxy view for CORS
# -----------------------
def proxy_image(request):
    url = request.GET.get('url')
    if not url:
        return HttpResponse('Missing URL', status=400)

    try:
        resp = requests.get(url, stream=True)
        resp.raise_for_status()

        content_type = resp.headers.get('Content-Type', 'image/webp')  # fallback
        response = HttpResponse(resp.content, content_type=content_type)

        # Add CORS headers
        response["Access-Control-Allow-Origin"] = "*"  # allow all origins
        response["Access-Control-Allow-Methods"] = "GET, OPTIONS"
        response["Access-Control-Allow-Headers"] = "*"

        return response

    except Exception as e:
        response = HttpResponse(f'Error fetching image: {e}', status=500)
        response["Access-Control-Allow-Origin"] = "*"
        return response


# -----------------------
# Upload view
# -----------------------

# api/views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from imagekitio import ImageKit
import json
import base64


@csrf_exempt
def upload_image(request):
    """
    Receives JSON: { "image_base64": "<base64 string>" }
    Uploads to ImageKit and returns URL.
    """
    try:
        data = json.loads(request.body)
        image_base64 = data.get("image_base64")

        if not image_base64:
            return JsonResponse({"error": "No image provided"}, status=400)

        # Remove prefix if present
        if "," in image_base64:
            image_base64 = image_base64.split(",", 1)[1]

        # Decode base64 → bytes
        try:
            file_bytes = base64.b64decode(image_base64)
        except Exception as e:
            return JsonResponse({"error": f"Invalid base64: {e}"}, status=400)

        # Upload to ImageKit
        try:
            upload_response = imagekit.upload(
                file=file_bytes,
                file_name="uploaded_image.png",
                options={"is_private_file": False, "use_unique_file_name": True}
            )
        except Exception as e:
            return JsonResponse({"error": f"ImageKit upload failed: {e}"}, status=500)

        return JsonResponse({
            "url": upload_response.url,
            "fileId": upload_response.file_id
        })

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    

# api/views.py

from django.http import JsonResponse
from imagekitio import ImageKit


def imagekit_auth(request):
    # Generate authentication parameters
    auth_params = imagekit.get_authentication_parameters()
    return JsonResponse(auth_params)


tinify.key = "kYbdBQTNhlhv1KX7Q7QB2cscD4vWK7vZ"

@csrf_exempt
def compress_image(request):
    if request.method == "POST":
        if "image" not in request.FILES:
            return JsonResponse({"error": "No image provided"}, status=400)

        image_file = request.FILES["image"]

        try:
            source = tinify.from_buffer(image_file.read())
            optimized_bytes = source.to_buffer()

            # Encode image as base64
            encoded = base64.b64encode(optimized_bytes).decode("utf-8")

            return JsonResponse({
                "optimized_image_base64": encoded,
                "mime_type": image_file.content_type
            })

        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid method"}, status=405)

from django.views.decorators.http import require_POST
from imagekitio.models.UploadFileRequestOptions import UploadFileRequestOptions

@csrf_exempt
@require_POST
def upload_image_files(request):
    try:
        body = json.loads(request.body)
        urls = body.get("urls", [])  # list of Supabase URLs

        uploaded_urls = []
        errors = []

        for url in urls:
            try:
                upload = imagekit.upload_file(
                    file=url,  # remote file url
                    file_name=url.split("/")[-1],
                    options=UploadFileRequestOptions(
                        response_fields=["tags"],
                        tags=["supabase-upload"]
                    )
                )

                if upload.response_metadata.raw.get("url"):
                    uploaded_urls.append(upload.response_metadata.raw["url"])
                else:
                    errors.append(f"Failed for {url}")
            except Exception as e:
                errors.append(str(e))

        return JsonResponse({"urls": uploaded_urls, "errors": errors})

    except Exception as e:
        return JsonResponse({"error": str(e)}, status=500)
    
def health_check(request):
    return JsonResponse({"status": "ok"})