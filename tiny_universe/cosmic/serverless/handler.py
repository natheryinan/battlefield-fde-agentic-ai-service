# cosmic/serverless/handler.py
from mangum import Mangum
from .main import app

handler = Mangum(app)
