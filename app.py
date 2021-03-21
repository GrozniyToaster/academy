from flask import Flask, request
from pydantic import BaseModel, validator, ValidationError, Field
from typing import List, Literal, Optional
from datetime import datetime
import re
import json
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


class OrderDB(db.Model):
    __tablename__ = 'order'

    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Float, nullable=False)
    region = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<OrderDB {self.id}>'


class CourierDB(db.Model):
    __tablename__ = 'courier'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(4), nullable=False)

    def __repr__(self):
        return f'<CourierDB({self.id}, {self.type}>'


class CourierRegion(db.Model):
    __tablename__ = 'courier__region'
    __table_args__ = (
        PrimaryKeyConstraint('id', 'region'),
        {},
    )
    id = db.Column(db.Integer, ForeignKey('courier.id'))
    region = db.Column(db.Integer, nullable=False)
    courier = relationship('CourierDB', backref="regions")

    def __repr__(self):
        return f'<CourierRegion({self.id}, {self.region})>'

class CourierWorkingHours(db.Model):
    __tablename__ = 'courier__working__hours'
    __table_args__ = (
        PrimaryKeyConstraint('id', 'begin', 'end'),
        {},
    )
    id = db.Column(db.Integer, ForeignKey('courier.id'))
    begin = db.Column(db.Integer, nullable=False)
    end = db.Column(db.Integer, nullable=False)
    courier = relationship('CourierDB', backref="working_hours")

class Assigned_Order(db.Model):
    id_courier = db.Column(db.Integer, nullable=False)
    id_order = db.Column(db.Integer, nullable=False, primary_key=True)
    time = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return '<Assigned_Order %r>' % self.id_order


class Time:
    def __init__(self, s: str = "00:00"):
        self.h, self.m = map(int, s.split(':'))
        assert 0 <= self.h <= 24 and 0 <= self.m <= 60  # check valid time
        self.sum = self.h * 60 + self.m

    def __str__(self):
        return f"{self.h}:{self.m}"


class TimeSegment:
    def __init__(self, seg: str = "00:00-00:00"):
        times = re.findall(r'^\d{2}:\d{2}-\d{2}:\d{2}$', seg)
        if not times:
            raise Exception("Not valid time")
        begin, end = (times[0]).split('-')
        self.begin = Time(begin)
        self.end = Time(end)
        if self.begin.sum >= self.end.sum:  # если конец раньше чем начало данные не валидны
            raise Exception("Not valid time")

    def __str__(self):
        return f"{self.begin:02d}-{self.end:02d}"


class Courier(BaseModel):
    id: Optional[int] = Field(alias='courier_id')
    type: Optional[Literal["foot", "bike", "car"]] = Field(alias='courier_type')
    regions: Optional[List[int]]
    working_hours: Optional[List[str]]

    @validator('working_hours')
    def working_hours_is_valid(cls, list_times: List[str]):
        try:
            for t in list_times:
                TimeSegment(t)
        except Exception as e:
            return ValidationError("Incorrect time")
        return list_times


class Order(BaseModel):
    id: int = Field(alias='order_id')
    weight: float
    region: int
    delivery_hours: List[str]

    @validator('id', 'weight', 'region')
    def field_is_positive(cls, v):
        assert v >= 0
        return v

    @validator('delivery_hours')
    def valid_time(cls, list_times: List[str]):
        try:
            for t in list_times:
                TimeSegment(t)
        except Exception as e:
            return ValidationError("Incorrect time")
        return list_times


class Id(BaseModel):
    id: int


class List_ids(BaseModel):
    couriers: Optional[List[Id]] = []
    orders: Optional[List[Id]] = []
    assign_time: Optional[datetime] = None


class List_validation_error(BaseModel):
    validation_error: List_ids = List_ids()


class Completed_order(BaseModel):
    courier_id: int
    order_id: int
    complete_time: datetime

    @validator('courier_id', 'order_id')
    def fields_is_positive(cls, v):
        assert v >= 0
        return v


def insert_courier(c: Courier):
    courier = CourierDB(id=c.id, type=c.type)
    courier.regions = [
        CourierRegion(region=r) for r in c.regions
    ]
    db.session.add(courier)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise Exception("Courier already exist")

def insert_order(o: Order):
    order = OrderDB(id=o.id, weight=o.weight, region=o.region)
    db.session.add(order)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise Exception("not uniq id")

def insert_complete(o: Completed_order):
    pass

def assign_orders_to_courier(courier: Courier):
    print(courier)
    return "WIP"


def update_db(courier_update: Courier):
    print("to update ", courier_update)
    return "WIP"


@app.route('/couriers', methods=['POST'])
def couriers_post():
    tmp_list = json.loads(request.get_data())
    valid_couriers_json = []
    not_valid = List_validation_error()

    for courier_posted in tmp_list["data"]:
        try:
            courier_obj = Courier.parse_obj(courier_posted)
            valid_couriers_json.append(courier_obj)
        except ValidationError:
            not_valid.validation_error.couriers.append(Id(id=courier_posted["courier_id"]))

    valid_requests = List_ids()

    for courier in valid_couriers_json:
        try:
            insert_courier(courier)
            valid_requests.couriers.append(Id(id=courier.id))
        except Exception as e:
            not_valid.validation_error.couriers.append(Id(id=courier.id))
    if not_valid.validation_error.couriers != []:
        return not_valid.json(exclude_defaults=True), 400
    return valid_requests.json(exclude_defaults=True), 200


@app.route('/couriers/<int:id>', methods=['PATCH'])
def couriers_patch(id):
    try:
        update_fields = Courier.parse_raw(request.get_data())
        update_fields.id = id
        ans = update_db(update_fields)
    except:
        return "Bad data", 400
    return ans


@app.route('/orders', methods=['POST'])
def orders_post():
    tmp_list = json.loads(request.get_data())
    valid_orders_json = []
    not_valid = List_validation_error()

    for order_posted in tmp_list["data"]:
        try:
            order_obj = Order.parse_obj(order_posted)
            valid_orders_json.append(order_obj)
        except ValidationError:
            not_valid.validation_error.orders.append(Id(id=order_posted["order_id"]))

    valid_requests = List_ids()

    for order in valid_orders_json:
        try:
            insert_order(order)
            valid_requests.orders.append(Id(id=order.id))
        except Exception as e:
            print(e)
            not_valid.validation_error.orders.append(Id(id=order.id))
    if not_valid.validation_error.orders != []:
        return not_valid.json(exclude_defaults=True), 400
    return valid_requests.json(exclude_defaults=True), 200


@app.route('/orders/assign', methods=['POST'])
def orders_assign_post():
    try:
        courier = Courier.parse_raw(request.get_data())
        answer = assign_orders_to_courier(courier)
    except:
        return "Bad Data", 400
    return answer


@app.route('/orders/complete', methods=['POST'])
def orders_complete_post():
    try:
        order = Completed_order.parse_raw(request.get_data())
        insert_complete(order)
    except:
        return "Bad value", 400
    return f"{{ \"order_id\": {order.order_id} }}", 200


if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=True)
