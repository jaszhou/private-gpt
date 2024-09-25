from flask import Flask 
from flask_cors import CORS #1 

app = Flask(__name__) #2 
CORS(app) #3
