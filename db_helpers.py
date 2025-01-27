import datetime

import qrcode

from dateutil.relativedelta import *
from math import radians, cos, sin, asin, sqrt

from sqlalchemy.engine import base
from sqlalchemy.ext.automap import automap_base
from sqlalchemy.orm import Session
from sqlalchemy import create_engine

Base = automap_base()

engine = create_engine(r"sqlite:///SelfStorage.db")

Base.prepare(engine, reflect=True)

Warehouses = Base.classes.warehouses
Boxes = Base.classes.boxes
Clients = Base.classes.clients
Storages = Base.classes.storages
Prices = Base.classes.prices
Orders = Base.classes.orders
T_Orders = Base.classes.t_orders

session = Session(engine)


def get_records(table, filter={}):
    if filter:
        return session.query(table).filter_by(**filter).all()
    return session.query(table).all()


def get_records_sql(sql):
    recordset = session.execute(sql)
    return([row._asdict() for row in recordset])


def add_client(context_data):
    new_client = Clients(
        title=context_data['title'],
        fio=context_data['fio'],
        phone=context_data['phone'],
        pass_id=context_data['pass_id'],
        birth_date=context_data['birth_date'],
        description=context_data['description'],
    )
    session.add(new_client)
    session.commit()
    return new_client.id


def add_order(context_data):
    new_order = Orders(
        title=context_data['title'],
        order_date=context_data['order_date'],
        client_id=context_data['client_id'],
        price_id=context_data['price_id'],
        storage_cnt=context_data['storage_cnt'],
        wrh_id=context_data['wrh_id'],
        rent_from=context_data['rent_from'],
        rent_to=context_data['rent_to'],
        description=context_data['description'],
    )
    session.add(new_order)
    session.commit()
    return new_order.id


def add_t_order(context_data):
    new_order = T_Orders(
        order_date=context_data['order_date'],
        order_sum=context_data['order_sum'],
        user_id=context_data['user_id'],
        warehouse_id=context_data['warehouse_id'],
        warehouse_title=context_data['warehouse_title'],
        stuff=context_data['stuff'],
        stuff_number=context_data['stuff_number'],
        fio=context_data['fio'],
        phone=context_data['phone'],
        pass_id=context_data['pass_id'],
        birth_date=context_data['birth_date'],
        rent_from=context_data['rent_from'],
        rent_to=context_data['rent_to']
    )
    session.add(new_order)
    session.commit()
    return new_order.id


def generate_qr(context_data):
    text = (
        f'{context_data["fio"]}.\n'
        f'Заказ № {context_data["order_id"]}, '
        f'Сгенерировано {datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S")}'
    )
    qr = qrcode.QRCode(version=1, box_size=6, border=3)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    return img


def make_dates(period):
    p1, p2 = period.split(' ')
    rent_from = datetime.datetime.now()
    if 'месяц' in p2:
        rent_to = rent_from + relativedelta(months=int(p1))
        return(rent_from, rent_to)
    elif 'недел' in p2:
        rent_to = rent_from + relativedelta(weeks=int(p1))
        return(rent_from, rent_to)
    return(rent_from, rent_from) 


def calc_payment(period, stuff, stuff_number):
    rent_from, rent_to = make_dates(period)
    cost = 0
    delta = relativedelta(rent_to, rent_from)
    for row in get_records_sql(f'SELECT period, price FROM v_prices WHERE storage_title = "{stuff}"'):
        if row['period'] == 'месяц':
            cost = cost + row['price'] * delta.months
        elif row['period'] == 'неделя':
            cost = cost + row['price'] * delta.weeks
        else:
            cost = 0
    return cost * stuff_number


def get_last_orders(user_id):
    sql = (
        "SELECT id, strftime('%d.%m.%Y', order_date) AS order_date_, "
        "order_sum, warehouse_title, stuff, stuff_number "
        "FROM t_orders "
        f"WHERE user_id = {user_id} "
        "ORDER BY order_date DESC "
        "LIMIT 3;"
    )
    reply_text = ''
    for row in get_records_sql(sql):
        reply_text += (
            f'Заказ {row["id"]} от {row["order_date_"]} на {row["order_sum"]}р., '
            f'склад {row["warehouse_title"]}, хранение {row["stuff"]}, мест {row["stuff_number"]}.\n'
        )
    return reply_text


def calc_distance(lat1, lon1):
    R = 6372.8
    dist = {}
    for warehouse in get_records(Warehouses):
        lat2 = warehouse.latitude
        lon2 = warehouse.longitude
        dLat = radians(lat2 - lat1)
        dLon = radians(lon2 - lon1)
        lat_1 = radians(lat1)
        lat_2 = radians(lat2)
        a = sin(dLat/2)**2 + cos(lat_1)*cos(lat_2)*sin(dLon/2)**2
        c = 2*asin(sqrt(a))
        dist[f'{warehouse.title}, {warehouse.address}'] = round(R * c, 2)
    return dict(sorted(dist.items(), key=lambda item: item[1], reverse=False))
