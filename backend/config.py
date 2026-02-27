import os
from dotenv import load_dotenv

load_dotenv()  # load variables from .env into environment

API_KEY = os.getenv("TFNSW_API_KEY")
BASE_URL = "https://api.transport.nsw.gov.au/v1/tp/departure_mon"