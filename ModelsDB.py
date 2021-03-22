from flask import Flask

from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from datetime import datetime

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///data.db?check_same_thread=False'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)




class OrderDB(db.Model):
    __tablename__ = 'orders'

    id = db.Column(db.Integer, primary_key=True)
    weight = db.Column(db.Float, nullable=False)
    region = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<OrderDB({self.id}, {self.weight}, {self.region})>'


class CourierDB(db.Model):
    __tablename__ = 'couriers'

    id = db.Column(db.Integer, primary_key=True)
    type = db.Column(db.String(4), nullable=False)

    def __repr__(self):
        return f'<CourierDB({self.id}, {self.type}>'


class CourierRegion(db.Model):
    __tablename__ = 'couriers_regions'
    __table_args__ = (
        PrimaryKeyConstraint('id', 'region'),
        {},
    )
    id = db.Column(db.Integer, ForeignKey('couriers.id'))
    region = db.Column(db.Integer, nullable=False)
    courier = relationship('CourierDB', cascade="all,delete", backref="regions")

    def __repr__(self):
        return f'<CourierRegion({self.id}, {self.region})>'


class CourierWorkingHours(db.Model):
    __tablename__ = 'couriers_working_hours'
    __table_args__ = (
        PrimaryKeyConstraint('id', 'begin', 'end'),
        {},
    )
    id = db.Column(db.Integer, ForeignKey('couriers.id'))
    begin = db.Column(db.Integer, nullable=False)
    end = db.Column(db.Integer, nullable=False)
    courier = relationship('CourierDB', cascade="all,delete", backref="working_hours")

    def __repr__(self):
        return f'<CourierWorkingHours({self.id}, {self.begin}, {self.end})>'


class Assigned_Order(db.Model):
    __tablename__ = 'assigned_orders'
    id_courier = db.Column(db.Integer, ForeignKey('couriers.id'))
    id_order = db.Column(db.Integer, ForeignKey('orders.id'), primary_key=True)
    time = db.Column(db.DateTime, default=datetime.utcnow)
    order = relationship('OrderDB', cascade="all,delete", backref="assigned")
    courier = relationship('CourierDB', cascade="all,delete", backref="assigned")

    def __repr__(self):
        return f'<Assigned_Order({self.id_order},{self.id_courier},{self.time})>'


class OrdersDeliveryHours(db.Model):
    __tablename__ = 'orders_delivery_hours'
    __table_args__ = (
        PrimaryKeyConstraint('id', 'begin', 'end'),
        {},
    )
    id = db.Column(db.Integer, ForeignKey('orders.id'))
    begin = db.Column(db.Integer, nullable=False)
    end = db.Column(db.Integer, nullable=False)
    order = relationship('OrderDB', cascade="all,delete", backref="delivery_hours")

    def __repr__(self):
        return f'<OrdersDeliveryHours({self.id}, {self.begin}, {self.end})>'
