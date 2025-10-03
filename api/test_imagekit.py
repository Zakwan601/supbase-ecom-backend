from imagekitio import ImageKit
import base64
import os
import sys

# Initialize ImageKit
imagekit = ImageKit(
    private_key="private_8wYbxoINX83O+QgkmJVErl8DRWA=",
    public_key="public_b1sQ/8elvKd9V/hGdmIbuNec55k=",
    url_endpoint="https://ik.imagekit.io/zakwan601"
)


# Path to local image for testing
image_path = "test_image.png"


upload = imagekit.upload(
    file=open("test_image.png", "rb"),
    file_name="my_file_name.jpg",
)

print("Upload binary", upload)

# Raw Response
print(upload.response_metadata.raw)

# print that uploaded file's ID
print(upload.file_id)