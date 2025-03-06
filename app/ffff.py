import datetime
user = User(username="Admin", email="dasdas@gmil.com")
user.set_password("123")
db.session.add(user)
db.session.commit()

r = Repka(repka_id=0, username="Admin")
db.session.add(r)
db.session.commit()

repkaLoop = RepkaLoop(repka_id=0)
db.session.add(repkaLoop)
db.session.commit()

repkanl = RepkaNotLoop(date=datetime.datetime.today().replace(microsecond=0, second=0), repka_id=0)
db.session.add(repkanl)
db.session.commit()

repkareq = RepkaRequests(repka_id=0, reboot=False, image=False)
db.session.add(repkareq)
db.session.commit()

rl = RepkaLogs(repka_id=0, date=datetime.datetime.today().replace(microsecond=0, second=0), log="sometext")
