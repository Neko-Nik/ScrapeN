"""
This file has all the necessary libraries for the project to run
any new library should be added here and imported in the respective files
"""

# FastAPI libraries
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse , PlainTextResponse , HTMLResponse, FileResponse
from fastapi import FastAPI, File, UploadFile , Form, Request, status, Response, Depends, BackgroundTasks, HTTPException
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.templating import Jinja2Templates
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
import uvicorn
from typing import Optional
from fastapi.staticfiles import StaticFiles



# Database libraries
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import TEXT, BOOLEAN
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import QueuePool


# Firebase
from firebase_admin import auth, credentials, initialize_app


# Parsing libraries
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin
import xml.etree.ElementTree as ET
from filelock import FileLock


# JS Scraping libraries
from seleniumwire import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from threading import Lock
from itertools import cycle


# other libraries
import json
import re
import time
import zipfile
import shutil
import hashlib
import stripe
import requests
import threading
import validators
import cloudscraper
import urllib.parse
from datetime import datetime
from pydantic import BaseModel
from functools import wraps


# read env variables
import dotenv
import configparser
import os


# Getting some constants from the constants.py file
from src.utils.base.constants import LOG_LEVEL, LOG_FILE_PATH

# Configure logging 
from src.utils.base.log_utils import configure_return_logger
logging = configure_return_logger(LOG_LEVEL=LOG_LEVEL,
                                  LOG_FILE_PATH=LOG_FILE_PATH)
