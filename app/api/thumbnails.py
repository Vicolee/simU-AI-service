from fastapi import APIRouter
from dotenv import load_dotenv, find_dotenv
import os
from .prompts import Prompts
from .request_models.ThumbnailRequest import ThumbnailInfo
from .response_models.thumbnailResponse import ThumbnailResponse
from openai import OpenAI
import base64
import boto3
import uuid
from PIL import Image
from io import BytesIO

from .helpers.backoff_retry import retry_with_exponential_backoff

# Load environment variables
load_dotenv(find_dotenv())

# Get AWS keys from environment variables
aws_secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
aws_public_key = os.getenv("AWS_ACCESS_KEY_ID")

# Initialize OpenAI and S3 clients
client = OpenAI()
s3 = boto3.resource('s3', region_name='us-east-2', aws_access_key_id=aws_public_key, aws_secret_access_key=aws_secret_key)

# Define S3 bucket name
bucket_name = 'sim-you-media'

secret_key = os.getenv("OPENAI_API_KEY")

# Initialize API router for thumbnails
thumbnails = APIRouter()

# TODO: Handle OpenAI rate limiting - 5 images per minute.
@thumbnails.post('/api/thumbnails', response_model=ThumbnailResponse)
def add_thumbnail(thumbnailInfo: ThumbnailInfo):
    """
    This function generates a thumbnail image based on the provided description using OpenAI's DALL-E model.
    The generated image is then stored in an S3 bucket and the URL of the image is returned.

    Args:
    thumbnailInfo (ThumbnailInfo): The ThumbnailInfo object which contains the world ID, owner ID, and description.

    Returns:
    str: The URL of the generated thumbnail image.
    """
    # Get prompt for generating the thumbnail
    prompt = Prompts.get_world_thumbnail_prompt(thumbnailInfo.description)

    # Generate image using OpenAI's DALL-E model
    response = generate_thumbnail_with_retries(prompt)

    # Resize
    image_bytes = base64.b64decode(response.data[0].b64_json)
    img = Image.open(BytesIO(image_bytes))
    resized_img = img.resize((256, 256))
    img_in_mem = BytesIO()
    resized_img.save(img_in_mem, 'JPEG')

    # Build file name
    file_name = "thumbnails/" + thumbnailInfo.worldID + ".jpeg"

    # Put image in S3 bucket
    obj = s3.Object(bucket_name, file_name)
    obj.put(Body=img_in_mem.getvalue())

    # Get bucket location
    location = boto3.client('s3').get_bucket_location(Bucket=bucket_name)['LocationConstraint']

    # Get object URL
    object_url = "https://%s.s3-%s.amazonaws.com/%s" % (bucket_name,location, file_name)
    
    response_obj = ThumbnailResponse(thumbnailURL=object_url)
    return response_obj

@retry_with_exponential_backoff
def generate_thumbnail_with_retries(prompt):
    response = client.images.generate(
        model="dall-e-3",
        prompt=prompt,
        size="1024x1024",
        quality="standard",
        n=1,
        response_format="b64_json",
    )
    return response