from flask import Flask
from app.config import Config
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from app.some_expr import SECRET, token
import telebot

app = Flask(__name__)
app.config.from_object(Config)
login = LoginManager()
login.init_app(app)
login.login_view = 'login'
db = SQLAlchemy(app)
migrate = Migrate(app, db)
bot = telebot.TeleBot(token=token, threaded=False)
#bot.remove_webhook()

#bot.set_webhook(url='https://spore.k-lab.su/' + SECRET)

from app import models, routes



