# -*- coding: utf-8 -*-
"""Application configuration.
Most configuration is set via environment variables.
For local development, use a .env file to set
environment variables.
"""
from pathlib import Path

from environs import Env

env = Env()
env.read_env()

ENV = env.str("FLASK_ENV", default="production")
DEBUG = ENV == "development"

# Database config
SECRET_KEY = env.str("SECRET_KEY")
SQLALCHEMY_DATABASE_URI = env.str("DATABASE_URI")
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Github app cofigs
GITHUBAPP_ID = env.int("GITHUBAPP_ID")
GITHUBAPP_SECRET = env.str("GITHUBAPP_SECRET")
with open(env.str("GITHUBAPP_KEY_PATH"), "rb") as key_file:
    GITHUBAPP_KEY = key_file.read()

# Github Auth configs
GITHUB_CLIENT_ID = env.str("GITHUB_CLIENT_ID")
GITHUB_CLIENT_SECRET = env.str("GITHUB_CLIENT_SECRET")

# Github Auth Token
GITHUB_TOKEN = env.str("GITHUB_TOKEN")

GITHUBREPO_OWNER = "OpenPecha"

# admin user
OP_ADMIN_USERS = env.str("OP_ADMIN_USERS")

# Form Securities
MAX_CONTENT_LENGTH = 1024 * 1024
UPLOAD_EXTENSIONS = [".jpg", ".png", ".jpeg"]
BOOK_ASSETS_UPLOAD_PATH = Path("/tmp/uploads")
