import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SQLALCHEMY_DATABASE_URI = f"mysql+mysqlconnector://{os.getenv('USER_BD')}:{os.getenv('PASS_BD')}@{os.getenv('ROOT_BD')}/{os.getenv('NAME_BD')}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
