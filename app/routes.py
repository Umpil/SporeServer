import datetime
import os
import re

from flask import jsonify, request, abort
from PIL import Image
import json
import base64
from io import BytesIO
from app.some_expr import SECRET
from app import app, db, bot
from flask_login import current_user, login_user
from app.models import User, Monitor, BotUsers
from flask import render_template, redirect, url_for, flash
from app.forms import LoginForm

from flask_login import login_required
from urllib.parse import urlparse
from app.validators_ import validate_area, validate_pyrge, validate_spray, validate_datetime
import telebot
from telebot import types


def parse_etap(name: str) -> str:
    if name == "Se":
        return "Отправка"
    elif name == "Sc":
        return "Сканирование"
    elif name == "Rs":
        return "Прокрутка до сканирования"
    elif name == "Py":
        return "Продув"
    elif name == "Sp":
        return "Напыление"
    elif name == "RSp":
        return "Прокрутка до напыления"
    elif name == "I":
        return "Инициализация"
    else:
        return "Ошибка"


def FindNext(dat: datetime.datetime, rep: int):
    monitor = Monitor.query.filter_by(Repka=rep).all()
    now = dat.timestamp()
    today = datetime.datetime.today().replace(second=0, microsecond=0).timestamp()
    min_date = None
    min_time = 10000000000000000000000000000
    if monitor:
        for mon in monitor:
            if mon.TimeStart.timestamp() - today > 0:
                if mon.TimeStart.timestamp() - now < min_time:
                    min_time = mon.TimeStart.timestamp() - now
                    min_date = mon
        if min_date:
            min_date.set_Status("Следующая")
            db.session.commit()
        else:
            pass


def UpdateNext(repka):
    all_ = Monitor.query.filter_by(Repka=repka).all()
    today = datetime.datetime.today().replace(second=0, microsecond=0).timestamp()
    min_date = None
    min_time = 1000000000000000000000
    for mon in all_:
        mon_time = mon.TimeStart.timestamp()
        if mon.Status == "Следующая":
            mon.set_Status("")
            db.session.commit()
        if min_time > mon_time - today > 0:
            min_time = mon_time - today
            min_date = mon.TimeStart
        if mon.Status == "В работе":
            if "Send" not in json.loads(mon.ControlStatus).keys() and datetime.datetime.today().timestamp() - mon.TimeStart.timestamp() > 14850:
                mon.set_Status("Истекло время получения результатов")
                db.session.commit()
    if min_date:
        need_date = Monitor.query.filter_by(Repka=repka, TimeStart=min_date).first()
        need_date.set_Status("Следующая")
        db.session.commit()


def CopyRow(repka, date, times, recall):
    next_date = Monitor.query.filter_by(Status="Следующая", Repka=repka).first()
    if not next_date:
        next_date = datetime.datetime.today().timestamp()
    else:
        next_date = next_date.TimeStart.timestamp()
    base_date = Monitor.query.filter_by(Repka=repka, TimeStart=date).first()
    Area = base_date.Area
    Pyrge = base_date.TimePyrge
    Spray = base_date.TimeSpray
    for i in range(times):
        check = Monitor.query.filter_by(Repka=int(repka),
                                        TimeStart=datetime.datetime.fromtimestamp(next_date + recall * 60).replace(
                                            second=0, microsecond=0)).first()
        if check:
            check.set_Area(Area)
            check.set_Pyrge(int(Pyrge))
            check.set_Spray(int(Spray))
            db.session.commit()
        else:
            m = Monitor(Repka=repka, TimeStart=datetime.datetime.fromtimestamp(next_date+recall*60).replace(second=0, microsecond=0), TimePyrge=int(Pyrge), Area=Area, TimeSpray=int(Spray))
            db.session.add(m)
            db.session.commit()
        next_date += recall * 60
    UpdateNext(repka)


# @app.route("/{}".format(SECRET), methods=["POST"])
# def telegram_webhook():
#     if request.headers.get('content-type') == 'application/json':
#         json_string = request.stream.read().decode('utf-8')
#         update = telebot.types.Update.de_json(json_string)
#         bot.process_new_updates([update])
#         return 'ok', 200
#     else:
#         abort(403)


@app.route('/')
@app.route('/index')
@login_required
def index():
    return redirect(url_for("login"))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('AdminHub'))
    form = LoginForm()
    if form.validate_on_submit():
        if form.validate_on_submit():
            user = User.query.filter_by(username=form.username.data).first()
            if user is None or not user.check_password(form.password.data):
                flash('Invalid username or password')
                return redirect(url_for('login'))
            login_user(user, remember=form.remember_me.data)
            next_page = request.args.get('next')
            if not next_page or urlparse(next_page).netloc != '':
                next_page = url_for(f'AdminHub')
            return redirect(next_page)
    return render_template('login.html', title='Вход', form=form)


@login_required
@app.route("/AdminHub", methods=["POST", "GET"])
def AdminHub():
    UpdateNext(0)
    if request.method == "POST":
        form = request.form
        needk = None
        if "Add" in list(form.keys()):
            repka = int(form["add_repka"])
            full_time = form["add_date"]
            full_time += f" {form['add_time']}"
            date = datetime.datetime.strptime(full_time, "%Y-%m-%d %H:%M").replace(second=0, microsecond=0)
            if validate_area(form["add_area"], ""):
                Area = form["add_area"]
            else:
                Area = "10x10"
            Pyrge = int(form["add_pyrge"])
            Spray = int(form["add_spray"])
            Ask = int(form["add_ask"])
            if "add_user" in list(form.keys()):
                username = form["add_user"]
            else:
                username = ""
            new_record = Monitor(Repka=repka, TimeStart=date, Area=Area, TimePyrge=Pyrge, TimeSpray=Spray, TimeAsk=Ask, username=username)
            db.session.add(new_record)
            db.session.commit()
        else:
            for k in list(form.keys()):
                if re.fullmatch(r"copy_\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d_\d+", k):
                    needk = k
            if needk:
                repka_id = int(needk.split("_")[2])
                date = datetime.datetime.strptime(needk.split("_")[1], "%Y-%m-%d %H:%M:%S").replace(second=0, microsecond=0)
                times = int(form["times"])
                recall = int(form["recall"])
                CopyRow(repka_id, date, times, recall)
        return redirect(url_for("AdminHub"))

    monitor = Monitor.query.filter(Monitor.TimeStart)
    repkas = Monitor.query.with_entities(Monitor.Repka).distinct().all()
    Next = {}
    InWork = {}
    for repka in repkas:
        Next[int(repka[0])] = Monitor.query.filter_by(Status="Следующая", Repka=int(repka[0])).first()
        InWork[int(repka[0])] = Monitor.query.filter_by(Status="В работе", Repka=int(repka[0])).all()
    return render_template("AdminHub.html", monitor=monitor, Next=Next, InWork=InWork, today=datetime.datetime.today())


@app.template_test("None")
def is_none(obj):
    return obj is None


@login_required
@app.route("/AdminHubEdit/<int:repka>/<string:t_strt>", methods=["GET", "POST"])
def StartEdit(repka, t_strt):
    monitor = Monitor.query.filter_by(Repka=int(repka), TimeStart=datetime.datetime.strptime(t_strt, "%Y-%m-%d %H:%M:%S")).first()
    if request.method == "POST":
        form = request.form
        if form["select"] == "Обновить":
            needUpdate = False
            area = form["area"]
            pyrge = form["pyrge"]
            spray = form["spray"]
            date = form["date"]
            tim = form["time"]
            if validate_area(area, monitor.Area):
                needUpdate = True
                monitor.set_Area(area)
            if validate_spray(spray, monitor.TimeSpray):
                monitor.set_Spray(spray)
                needUpdate = True
            if validate_datetime(date, tim):
                year, month, day = date.split("-")
                hour, minute = tim.split(":")
                check_date = datetime.datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute)).replace(second=0, microsecond=0)
                monitor.set_Start = check_date
                needUpdate = True
            if validate_pyrge(pyrge, monitor.TimePyrge):
                monitor.set_Pyrge(pyrge)
                needUpdate = True
            if needUpdate:
                db.session.commit()
        if form["select"] == "Удалить":
            Monitor.query.filter_by(Repka=int(repka), TimeStart=datetime.datetime.strptime(t_strt, "%Y-%m-%d %H:%M:%S")).delete()
            db.session.commit()
            return redirect(url_for(f'AdminHub'))
    return render_template("edit_date.html", monitor=monitor)


@app.route("/update/log", methods=["POST", "PUT"])
def update_log():
    dict_data = request.get_json()
    username = dict_data["un"]
    password = dict_data["pw"]
    user = User.query.filter_by(username=username).first()

    if user is not None and user.check_password(password):
        repka_id = int(dict_data["ri"])
        date = datetime.datetime.fromisoformat(dict_data["date"])
        monitor = Monitor.query.filter_by(TimeStart=date, Repka=repka_id).first()
        etap = dict_data["e"]
        if etap == "err":
            if monitor.ControlStatus:
                buff = json.loads(monitor.ControlStatus)
                rus_etap = parse_etap(etap)
                buff[rus_etap] = dict_data["etap_time"]
                monitor.set_Control(buff)
                db.session.commit()
                monitor.set_Status("Закончилось с ошибкой")
                db.session.commit()
                return "ok"
            else:
                rus_etap = parse_etap(etap)
                buff = {rus_etap: dict_data["et"]}
                monitor.set_Control(buff)
                db.session.commit()
                monitor.set_Status("Закончилось с ошибкой")
                db.session.commit()
                return "ok"
        etap_time = dict_data["et"]

        if monitor.Status != "В работе" and monitor.Status != "Отработано":
            monitor.set_Status("В работе")
            db.session.commit()
        if monitor.ControlStatus:
            buff = json.loads(monitor.ControlStatus)
            rus_etap = parse_etap(etap)
            buff[rus_etap] = etap_time
            monitor.set_Control(buff)
            db.session.commit()
            return "ok"
        else:
            rus_etap = parse_etap(etap)
            buff = {rus_etap: etap_time}
            monitor.set_Control(buff)
            db.session.commit()
            return "ok"
    return "bad"


@app.route("/check", methods=["POST", "PUT"])
def check():
    dict_data = request.get_json()
    username = dict_data["un"]
    password = dict_data["pw"]
    user = User.query.filter_by(username=username).first()
    if user is not None and user.check_password(password):
        repka_id = int(dict_data["ri"])
        UpdateNext(repka_id)
        monitor = Monitor.query.filter_by(Repka=repka_id, Status="Следующая").first()
        if monitor:
            Next = monitor.TimeStart.replace(second=0, microsecond=0).timestamp()
            Area = monitor.Area
            Pyrge = monitor.TimePyrge
            Spray = monitor.TimeSpray
            Ask = monitor.TimeAsk
            response = {"Next": int(Next), "Area": Area, "Pyrge": Pyrge, "Spray": Spray, "TimeAsk": Ask}
            return jsonify(response)
        else:
            return jsonify({"Next": 0, "TimeAsk": 5})
    return jsonify({"Next": 0, "TimeAsk": 5})


@app.route("/upload/test", methods=["POST", "PUT"])
def test():
    dict_data = request.get_json()
    print(dict_data["g"])
    return jsonify({"Try": 123})


@app.route("/upload/add/photo")
def add_image():
    dict_data = request.get_json()
    username = dict_data["un"]
    password = dict_data["pw"]
    user = User.query.filter_by(username=username).first()
    if user is not None and user.check_password(password):
        img = dict_data["im"]
        code = dict_data["cd"]
        rep_id = int(dict_data["ri"])
        date = datetime.datetime.fromisoformat(dict_data["d"])
        img = base64.b64decode(img)
        img = BytesIO(img)
        img = Image.open(img)
        if os.path.exists(f"/home/robot/{rep_id}/{date}"):
            os.mkdir(f"/home/robot/{rep_id}/{date}")

        monitor = Monitor.query.filter_by(TimeStart=date, Repka=rep_id).first()
        if code == "f":
            img.save(f"/home/robot/{rep_id}/{date}/first_image.jpg")
            monitor.set_FirstPhoto(f"/home/robot/{rep_id}/{date}/first_image.jpg")
            db.session.commit()
        elif code == "b":
            img.save(f"/home/robot/{rep_id}/{date}/best_image.jpg")
            monitor.set_BestPhoto(f"/home/robot/{rep_id}/{date}/best_image.jpg")
            db.session.commit()
        elif code == "l":
            img.save(f"/home/robot/{rep_id}/{date}/last_image.jpg")
            monitor.set_LastPhoto(f"/home/robot/{rep_id}/{date}/last_image.jpg")
            db.session.commit()
            monitor.set_Status("Отработано")
            db.session.commit()
            FindNext(monitor.TimeStart, int(rep_id))
            bou = BotUsers.query.filter_by(username=username).all()
            result = monitor.Result
            if bou:
                text = f"Дата : {monitor.TimeStart}\n" \
                       f"Устройство : {monitor.Repka}\n" \
                       f"  Обнаружено\n" \
                       f"Мучнистой росы : {result['Mu']}\n" \
                       f"Жёлтой ржавчины : {result['Ru']}\n" \
                       f"Пиренеофоры : {result['Pi']}\n"
                for bo in bou:
                    if not bo.username == "Admin":
                        f = open(f"/home/robot/{rep_id}/{date}/first_image.jpg", "rb")
                        bot.send_photo(int(bo.chat_id), f, caption="Первое фото")
                        f.close()
                        f = open(f"/home/robot/{rep_id}/{date}/best_image.jpg", "rb")
                        bot.send_photo(int(bo.chat_id), f, caption="Наибольшее количество спор")
                        f.close()
                        f = open(f"/home/robot/{rep_id}/{date}/last_image.jpg", "rb")
                        bot.send_photo(int(bo.chat_id), f, caption="Последнее фото")
                        f.close()
                        bot.send_message(int(bo.chat_id), text=text)
            bo = BotUsers.query.filter_by(username="Admin").first()
            text = f"Дата : {monitor.TimeStart}\n" \
                   f"Устройство : {monitor.Repka}\n" \
                   f"  Обнаружено\n" \
                   f"Мучнистой росы : {result['Mu']}\n" \
                   f"Жёлтой ржавчины : {result['Ru']}\n" \
                   f"Пиренеофоры : {result['Pi']}\n"
            f = open(f"/home/robot/{rep_id}/{date}/first_image.jpg", "rb")
            bot.send_photo(int(bo.chat_id), f, caption="Первое фото")
            f.close()
            f = open(f"/home/robot/{rep_id}/{date}/best_image.jpg", "rb")
            bot.send_photo(int(bo.chat_id), f, caption="Наибольшее количество спор")
            f.close()
            f = open(f"/home/robot/{rep_id}/{date}/last_image.jpg", "rb")
            bot.send_photo(int(bo.chat_id), f, caption="Последнее фото")
            f.close()
            bot.send_message(int(bo.chat_id), text=text)
        elif code == "o":
            j = 0
            for i in range(100):
                if os.path.exists(f"/home/robot/{rep_id}/{date}/other_{i}.jpg"):
                    j += 1
                else:
                    break
            img.save(f"/home/robot/{rep_id}/{date}/{j+1}.jpg")
        else:
            return "Ok"


@app.route("/upload/logimage", methods=["POST", "PUT"])
def upload_log_image():
    dict_data = request.get_json()
    username = dict_data["un"]
    password = dict_data["pw"]
    user = User.query.filter_by(username=username).first()

    if user is not None and user.check_password(password):

        text = dict_data["f"]
        rep_id = int(dict_data["ri"])
        result = dict_data["re"]
        date = datetime.datetime.fromisoformat(dict_data["d"])

        if text == "g":
            txt = "Всё в порядке"
        elif text == "c":
            txt = "Калибровка"
        elif text == "s":
            txt = "Сканирование"
        elif text == "k":
            txt = "Клапаны"
        else:
            txt = "Неизвестная ошибка"
        with open(f"/home/robot/{rep_id}/{date}/log.txt", "w", encoding="utf-8") as f:
            f.write(txt)

        monitor = Monitor.query.filter_by(TimeStart=date, Repka=rep_id).first()
        monitor.set_Result(result)
        db.session.commit()

        return {"KOK": "Ok"}
    else:
        return "What"


@bot.message_handler(commands=['start'])
def BaseMessageHandler(message):
    try:
        bot.delete_message(message.from_user.id, message.message.id)
    except Exception as e:
        print("start")
    user = BotUsers.query.filter_by(chat_id=message.from_user.id).first()
    if user is None:
        kb = types.InlineKeyboardMarkup(row_width=1)
        auth_key = types.InlineKeyboardButton(text="Авторизация", callback_data="Auth")
        kb.add(auth_key)
        bot.send_message(message.from_user.id, text="Вы не авторизированы", reply_markup=kb)
    else:
        kb = types.InlineKeyboardMarkup(row_width=1)
        if user.username == "Admin":
            monitor = Monitor.query.all()
        else:
            monitor = Monitor.query.filter_by(username=user.username).all()
        repk_list = []
        if monitor:
            for mon in monitor:
                if mon.Repka not in repk_list:
                    repk_list.append(mon.Repka)
                    key = types.InlineKeyboardButton(text=f"{mon.Repka}", callback_data=f"Show_{mon.Repka}")
                    kb.add(key)
            bot.send_message(message.from_user.id, text="Выберите устройство", reply_markup=kb)
        else:
            bot.send_message(message.from_user.id, text="Нет зарегистрированных устройств", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: re.fullmatch(r"Show_\d+", call.data))
def ShowRepka(call):
    try:
        bot.delete_message(call.from_user.id, call.message.id)
    except Exception as e:
        print(e)
    repka_id = int(call.data.split("_")[1])
    records = Monitor.query.filter_by(Repka=repka_id).all()
    if records:
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton(text="Назад", callback_data="tostart"))
        for record in records:
            key = types.InlineKeyboardButton(text=f"{record.Status}\n{record.TimeStart}", callback_data=f"ShowConfig_{repka_id}_{record.TimeStart}")
            kb.add(key)

        bot.send_message(call.from_user.id, text="Нажмите на дату для детального просмотра", reply_markup=kb)
    else:
        bot.send_message(call.from_user.id, text="Отсутствуют зарегистрированные запуски")
        BaseMessageHandler(call)


@bot.callback_query_handler(func=lambda call: re.fullmatch(r"tostart", call.data))
def SendToStart(call):
    try:
        bot.delete_message(call.from_user.id, call.message.id)
    except Exception as e:
        print("start")
    BaseMessageHandler(call)


@bot.callback_query_handler(func=lambda call: re.fullmatch(r"ShowConfig_\d+_\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d", call.data))
def ShowConfig(call):
    try:
        bot.delete_message(call.from_user.id, call.message.id)
    except Exception as e:
        print("start")
    repka_id = int(call.data.split("_")[1])
    UpdateNext(repka_id)
    date = datetime.datetime.strptime(call.data.split("_")[2], "%Y-%m-%d %H:%M:%S")
    monitor = Monitor.query.filter_by(Repka=repka_id, TimeStart=date).first()
    text = f"Сетка сканирования: {monitor.Area}\n" \
           f"Период напыления: {monitor.TimeSpray}\n" \
           f"Период продува: {monitor.TimePyrge}\n" \
           f"Период обращения к серверу: {monitor.TimeAsk}\n"
    kb = types.InlineKeyboardMarkup()
    key_res = types.InlineKeyboardButton(text="Результат", callback_data=f"Result_{repka_id}_{monitor.TimeStart}")
    key_control = types.InlineKeyboardButton(text="Контроль отработки", callback_data=f"Control_{repka_id}_{monitor.TimeStart}")
    key_photos = types.InlineKeyboardButton(text="Фотографии", callback_data=f"Photo_{repka_id}_{monitor.TimeStart}")
    key_back = types.InlineKeyboardButton(text="Назад", callback_data=f"Show_{repka_id}")
    kb.add(key_res, key_control, key_photos, key_back)
    bot.send_message(call.from_user.id, text=text, reply_markup=kb)


@bot.callback_query_handler(func=lambda call: re.fullmatch(r"Result_\d+_\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d", call.data))
def ShowResult(call):
    try:
        bot.delete_message(call.from_user.id, call.message.id)
    except Exception as e:
        print("start")
    repka_id = int(call.data.split("_")[1])
    date = datetime.datetime.strptime(call.data.split("_")[2], "%Y-%m-%d %H:%M:%S")
    monitor = Monitor.query.filter_by(Repka=repka_id, TimeStart=date).first()
    kb = types.InlineKeyboardMarkup()
    key_back = types.InlineKeyboardButton(text="Назад", callback_data=f"ShowConfig_{repka_id}_{date}")
    kb.add(key_back)
    if monitor.Result:
        bot.send_message(call.from_user.id, text=monitor.Result, reply_markup=kb)
    else:
        bot.send_message(call.from_user.id, text="Результат отсутствует", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: re.fullmatch(r"Control_\d+_\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d", call.data))
def ShowContol(call):
    try:
        bot.delete_message(call.from_user.id, call.message.id)
    except Exception as e:
        print("start")
    repka_id = int(call.data.split("_")[1])
    date = datetime.datetime.strptime(call.data.split("_")[2], "%Y-%m-%d %H:%M:%S")
    monitor = Monitor.query.filter_by(Repka=repka_id, TimeStart=date).first()
    kb = types.InlineKeyboardMarkup()
    key_back = types.InlineKeyboardButton(text="Назад", callback_data=f"ShowConfig_{repka_id}_{date}")
    kb.add(key_back)
    if monitor.ControlStatus:
        bot.send_message(call.from_user.id, text=monitor.ControlStatus, reply_markup=kb)
    else:
        bot.send_message(call.from_user.id, text="Не было в обработке", reply_markup=kb)


@bot.callback_query_handler(func=lambda call: re.fullmatch(r"Photo_\d+_\d\d\d\d-\d\d-\d\d \d\d:\d\d:\d\d", call.data))
def ShowPhoto(call):
    try:
        bot.delete_message(call.from_user.id, call.message.id)
    except Exception as e:
        print("start")
    repka_id = int(call.data.split("_")[1])
    date = datetime.datetime.strptime(call.data.split("_")[2], "%Y-%m-%d %H:%M:%S")
    monitor = Monitor.query.filter_by(Repka=repka_id, TimeStart=date).first()
    kb = types.InlineKeyboardMarkup()
    key_back = types.InlineKeyboardButton(text="Назад", callback_data=f"ShowConfig_{repka_id}_{date}")
    kb.add(key_back)
    if monitor.FirstPhoto:
        img = open(monitor.FirstPhoto, "rb")
        bot.send_photo(call.from_user.id, photo=img, caption="Первая фотография")
        img.close()
    else:
        bot.send_message(call.from_user.id, text="Первая фотография отсутсвует")
    if monitor.BestPhoto:
        img = open(monitor.BestPhoto, "rb")
        bot.send_photo(call.from_user.id, photo=img, caption="Лучшая фотография")
        img.close()
    else:
        bot.send_message(call.from_user.id, text="Лучшая фотография отсутсвует")
    if monitor.LastPhoto:
        img = open(monitor.LastPhoto, "rb")
        bot.send_photo(call.from_user.id, photo=img, caption="Последняя фотография")
        img.close()
    else:
        bot.send_message(call.from_user.id, text="Последняя фотография отсутствует")
    bot.send_message(call.from_user.id, reply_markup=kb, text="Выберите")


@bot.callback_query_handler(func=lambda call: re.fullmatch("Auth", call.data))
def HandleAuthorization(message):
    mess = bot.send_message(message.from_user.id, text="Введите логин")
    bot.register_next_step_handler(mess, check_login)


def check_login(message):
    try:
        bot.delete_message(message.chat.id, message.message.id)
    except Exception:
        print("check_login")

    users = User.query.filter_by(username=message.text).first()
    if users is not None:
        mess = bot.send_message(message.from_user.id, text="Введите пароль")
        bot.register_next_step_handler(mess, check_parol, message.text)
    else:
        bot.send_message(message.from_user.id, text="login")


def check_parol(message, username: str):
    try:
        bot.delete_message(message.chat.id, message.message.id)
    except Exception:
        print("check_login")
    user = User.query.filter_by(username=username).first()
    if user.check_password(message.text):
        bot.send_message(message.from_user.id, text="Успешная авторизация")
        bu = BotUsers(username=username, chat_id=message.from_user.id, registered=True)
        db.session.add(bu)
        db.session.commit()
    else:
        bot.send_message(message.from_user.id, text="parol")



if __name__ == "__main__":
    app.run(debug=True, host="192.168.0.3", port=8080)
