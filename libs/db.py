from motor import motor_asyncio
from libs.config.settings import get_settings
from enum import Enum


settings = get_settings()


class Collections(str, Enum):
    users = "users"
    posts = "posts"
    comments = "comments"
    likes = "likes"
    ratings = "product_ratings"
    comments_likes = "comments_likes"
    likes_comments = "likes_comments"
    totps = "totps"
    products = "products"
    productCategories = "product_categories"
    authsessions = "authsessions"
    throttles = "throttles"
    carts = "carts"
    cart_items = "cart_items"
    orders = "orders"
    order_items = "order_items"


client = motor_asyncio.AsyncIOMotorClient(settings.db_url)


_db = client[settings.db_name]
