from api.imagekit_config import imagekit


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
