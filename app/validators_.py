from datetime import datetime


def validate_area(area: str, now: str) -> bool | None:
    if area == now:
        return None
    if "x" in area:
        delim = "x"
    elif "х" in area:
        delim = "х"
    else:
        return False
    w, h = area.split(delim)[0], area.split(delim)[1]

    if h.isnumeric():
        h = int(h)
        if not 1 <= h <= 65:
            return False
    else:
        return False

    if w.isnumeric():
        w = int(w)
        if not 1 <= w <= 23:
            return False
    else:
        return False

    return True


def validate_pyrge(pyrge: str | int, now: str) -> bool | None:
    if pyrge == now:
        return False
    if isinstance(pyrge, str):
        if pyrge.isnumeric():
            pyrge = int(pyrge)
        else:
            return False
    if not 1 <= pyrge <= 10:
        return False
    return True


def validate_spray(spray: str | int, now: str) -> bool | None:
    if spray == now:
        return False
    if isinstance(spray, str):
        if spray.isnumeric():
            spray = int(spray)
        else:
            return False
    if not 1 <= spray <= 120:
        return False
    return True


def validate_recall(recall: str | int, now: str) -> bool | None:
    if recall == now:
        return False
    if isinstance(recall, str):
        if recall.isnumeric():
            recall = int(recall)
        else:
            return False
    if not 1 <= recall <= 360:
        return False
    return True


def validate_name(name: str, now: str) -> bool | None:
    if name == "Введите имя":
        return False
    elif name == now:
        return False
    else:
        return True


def validate_datetime(date: str, time: str) -> bool:
    try:
        year, month, day = date.split("-")
        hour, minute = time.split(":")
    except Exception:
        return False
    try:
        check_date = datetime(year=int(year), month=int(month), day=int(day), hour=int(hour), minute=int(minute))
        ts_check = check_date.timestamp()
        today = datetime.today().timestamp()
        if ts_check - today < 0:
            raise Exception
    except Exception as e:
        print(e)
        return False
    return True


