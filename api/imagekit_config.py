import os

from dotenv import load_dotenv
from imagekitio import ImageKit

load_dotenv()

imagekit = ImageKit(
    private_key=os.environ["IMAGEKIT_PRIVATE_KEY"],
    public_key=os.environ["IMAGEKIT_PUBLIC_KEY"],
    url_endpoint=os.environ["IMAGEKIT_URL_ENDPOINT"],
)
