import datetime
import json
import os.path

from app import db
from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin
from app import login, app
default = datetime.datetime.fromtimestamp(datetime.datetime.today().replace(second=0, microsecond=0).timestamp() + 86400)
BaseArea = "30x15"
BasePyrge = 1
BaseSpray = 5
BaseAsk = 5
BaseResult = ""
BaseStr = ""


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), index=True, unique=True)
    chat_id = db.Column(db.Integer, unique=True)
    password_hash = db.Column(db.String(128))

    def set_chat_id(self, chat_id):
        self.chat_id = chat_id

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return '<User {}>'.format(self.username)


class BotUsers(db.Model):
    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    chat_id = db.Column(db.Integer, nullable=True)
    username = db.Column(db.Integer, nullable=False)
    registered = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return '<BotUsers {}>'.format(self.chat_id)


class Monitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    Repka = db.Column(db.Integer, nullable=False)
    username = db.Column(db.String(64), nullable=True)
    Name = db.Column(db.String(128), default="NoName")
    Status = db.Column(db.String(16), default=BaseStr)

    Area = db.Column(db.String(5), default=BaseArea)
    TimePyrge = db.Column(db.Integer, default=BasePyrge)
    TimeSpray = db.Column(db.Integer, default=BaseSpray)
    TimeStart = db.Column(db.DateTime, default=default)
    TimeAsk = db.Column(db.Integer, default=BaseAsk)

    Result = db.Column(db.String(64), default=BaseStr)
    FirstPhoto = db.Column(db.String(64), default=BaseStr)
    BestPhoto = db.Column(db.String(64), default=BaseStr)
    LastPhoto = db.Column(db.String(64), default=BaseStr)
    ControlStatus = db.Column(db.String(256), default=BaseStr)

    def set_Control(self, control: dict):
        self.ControlStatus = json.dumps(control)

    def set_Area(self, area):
        self.Area = area

    def set_Start(self, start):
        self.TimeStart = start

    def set_Spray(self, spray):
        self.TimeSpray = int(spray)

    def set_Pyrge(self, pyrge):
        self.TimePyrge = int(pyrge)

    def set_Ask(self, ask):
        self.TimeAsk = int(ask)

    def set_name(self, name: str):
        self.Name = name

    def set_username(self, username: str):
        self.username = username

    def set_Status(self, status: str):
        self.Status = status

    def set_Result(self, result: dict):
        vect_string = ""
        for key, value in result.items():
            vect_string += f"{key} : {value}"
        self.Result = vect_string

    def set_FirstPhoto(self, pathto: str):
        if os.path.exists(pathto):
            self.FirstPhoto = pathto
        else:
            raise ValueError

    def set_BestPhoto(self, pathto: str):
        if os.path.exists(pathto):
            self.BestPhoto = pathto
        else:
            raise ValueError

    def set_LastPhoto(self, pathto):
        if os.path.exists(pathto):
            self.LastPhoto = pathto
        else:
            raise ValueError

    def __repr__(self):
        return '<Monitor {}>'.format(self.repka_id)


@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'User': User, 'Monitor': Monitor, 'BotUsers': BotUsers}


@login.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))