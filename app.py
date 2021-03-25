from flask import request
from pydantic import ValidationError
from ValidatorModels import CourierOptional, CourierStrong, Completed_order, Order, List_ids, List_validation_error, \
    TimeSegment, Id

from ModelsDB import app, db, CourierDB, CourierWorkingHours, CourierRegion, OrderDB, OrdersDeliveryHours, \
    Assigned_Order, Rating

from sqlalchemy import text, and_
from datetime import datetime

import json

from typing import List

lifting_capacity = {
    'foot': 10,
    'bike': 15,
    'car': 50
}

payment_c = {
    'foot': 2,
    'bike': 5,
    'car': 9
}


def calculate_rating(id: int):
    ranges = db.session.query(Rating).filter_by(id=id).all()
    if not ranges:
        return None, 0
    t = float('inf')
    payment = 0
    for r in ranges:
        payment += r.count_foot * payment_c['foot']
        payment += r.count_bike * payment_c['bike']
        payment += r.count_car * payment_c['car']
        t = min(t, r.sum_dt / (r.count_foot + r.count_bike + r.count_car))
    rating = (60 * 60 - min(t, 60 * 60)) / (60 * 60) * 5
    payment *= 500
    return rating, payment


def get_data(id: int):
    cDB = db.session.query(CourierDB).filter_by(id=id).one()
    rating, payment = calculate_rating(id)
    ans = CourierOptional()
    ans.id = id
    ans.type = cDB.type
    ans.regions = [r.region for r in cDB.regions]
    ans.working_hours = [TimeSegment.by_sums(wh.begin, wh.end) for wh in cDB.working_hours]
    ans.rating = rating
    ans.earnings = payment
    return ans.json(exclude_defaults=True)


def insert_courier(c: CourierStrong):
    courier = CourierDB(id=c.id, type=c.type)
    courier.regions = [
        CourierRegion(region=r) for r in c.regions
    ]
    courier.working_hours = [
        CourierWorkingHours(begin=wh.begin.sum, end=wh.end.sum) for wh in c.working_hours
    ]
    db.session.add(courier)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise Exception("Courier already exist")


def insert_order(o: Order):
    order = OrderDB(id=o.id, weight=o.weight, region=o.region)
    order.delivery_hours = [
        OrdersDeliveryHours(begin=dh.begin.sum, end=dh.end.sum) for dh in o.delivery_hours
    ]
    db.session.add(order)
    try:
        db.session.commit()
    except:
        db.session.rollback()
        raise Exception("not uniq id")


def recalculate_rating(courier_id, order_id, region, dt, type):
    try:
        rec = db.session.query(Rating).filter_by(id=courier_id, region=region).one()
        rec.sum_dt += round(dt.total_seconds())

    except:
        rec = Rating(id=courier_id, region=region, sum_dt=round(dt.total_seconds()),
                     count_foot=0, count_bike=0, count_car=0)
        db.session.add(rec)
    if type == 'foot':
        rec.count_foot += 1
    elif type == 'bike':
        rec.count_bike += 1
    else:
        rec.count_car += 1
    db.session.commit()


def insert_complete(o: Completed_order):
    cur_o = db.session.query(OrderDB).filter_by(id=o.order_id).one()
    if cur_o.completed:
        return
    cur_rec = db.session.query(Assigned_Order).filter_by(id_order=o.order_id, id_courier=o.courier_id).one()
    recalculate_rating(o.courier_id,
                       o.order_id,
                       cur_o.region,
                       o.complete_time.replace(tzinfo=None) - cur_rec.courier.time_last_order,
                       cur_rec.type
                       )

    cur_o.completed = True
    cur_rec.courier.time_last_order = o.complete_time
    db.session.query(Assigned_Order).filter_by(id_order=o.order_id, id_courier=o.courier_id).delete()
    db.session.commit()


def intersection_segments(a1, b1, a2, b2):
    return not (
            a1 < a2 and b1 < a2
            or
            a1 > b2 and b1 > b2
    )


def segregate(b, e):
    time = []
    if b < e:
        if b + 1 <= e - 1:
            time.append([b + 1, e - 1])
    else:
        if b != 23 * 60 + 59:
            time.append([b + 1, 23 * 60 + 59])
        if e != 0:
            time.append([0, e - 1])
    return time


def intersection_times(b1, e1, b2, e2):
    time1 = segregate(b1, e1)
    time2 = segregate(b2, e2)
    for [a, b] in time1:
        for [c, d] in time2:
            if intersection_segments(a, b, c, d):
                return True
    return False


def import_data_from_db(courier: CourierOptional):
    courier_db = db.session.query(CourierDB).filter_by(id=courier.id).one()
    regions = [r.region for r in courier_db.regions]
    capacity = lifting_capacity[courier_db.type]

    vocant_orders = db.session.query(OrderDB).filter(
        and_(text(f'orders_completed = False AND orders_weight <= {capacity}'),
             OrderDB.region.in_(regions))
    ).order_by(OrderDB.weight).all()

    orders = []
    cur_size = 0
    overfow = False

    for order in vocant_orders:
        if order.assigned:
            continue
        if overfow:
            break
        added = False
        for dh in order.delivery_hours:
            if added or overfow:
                break
            for wh in courier_db.working_hours:
                if added or overfow:
                    break
                if intersection_times(wh.begin, wh.end, dh.begin, dh.end):
                    if cur_size + order.weight > capacity:
                        overfow = True
                        break
                    orders.append(order.id)
                    cur_size += order.weight
                    added = True

    return orders, courier_db


def add_rec_assigned_order(orders: List[int], courier: CourierDB):
    if orders:
        time = datetime.utcnow()
        courier.assigned = [
            Assigned_Order(id_order=oid, time=time, type=courier.type) for oid in orders
        ]
        courier.time_last_order = time
        db.session.commit()
        ans = List_ids()
        ans.orders = orders
        ans.assign_time = courier.assigned[0].time
        ans = ans.json(exclude_defaults=True)
    else:
        ans = "{\"orders\": []}"

    return ans


def assign_orders_to_courier(courier: CourierOptional):
    # checkin order availability
    orders = db.session.query(Assigned_Order).filter_by(id_courier=courier.id).all()
    if orders:
        ans = List_ids()
        ans.orders = [order.id_order for order in orders]
        ans.assign_time = orders[0].time
        return ans.json(exclude_defaults=True)

    orders, courier_db = import_data_from_db(courier)
    return add_rec_assigned_order(orders, courier_db)


def correct_assigned_orders(c: CourierOptional):
    orders = db.session.query(Assigned_Order).filter_by(
        id_courier=c.id
    ).all()
    capacity = lifting_capacity[c.type]
    for order in orders:
        if order.order.weight > capacity or order.order.region not in c.regions:
            db.session.query(Assigned_Order).filter_by(id_order=order.id_order).delete()
            db.session.commit()
            continue
        intersec = False
        for wh in c.working_hours:
            for dh in order.order.delivery_hours:
                intersec = intersection_times(wh.begin.sum, wh.end.sum, dh.begin, dh.end)
        if not intersec:
            db.session.query(Assigned_Order).filter_by(id_order=order.id_order).delete()

    orders = db.session.query(Assigned_Order).filter_by(
        id_courier=c.id
    ).all()
    sorted_orders = sorted(orders, key=lambda x: x.order.weight)
    cur_size = 0
    for o in sorted_orders:
        if o.order.weight + cur_size <= capacity:
            cur_size += o.order.weight
        else:
            db.session.delete(o)
    db.session.commit()


def update_db(courier_update: CourierOptional):
    current_courier = db.session.query(CourierDB).filter_by(id=courier_update.id).one()
    if courier_update.type is not None:
        current_courier.type = courier_update.type
    if courier_update.regions is not None:
        db.session.query(CourierRegion).filter_by(id=courier_update.id).delete()
        current_courier.regions = [CourierRegion(region=r) for r in courier_update.regions]
    if courier_update.working_hours is not None:
        db.session.query(CourierWorkingHours).filter_by(id=courier_update.id).delete()
        current_courier.working_hours = [
            CourierWorkingHours(begin=wh.begin.sum, end=wh.end.sum) for wh in courier_update.working_hours
        ]
    db.session.commit()
    correct_assigned_orders(courier_update)

    # forming answer
    courier_update.type = current_courier.type
    courier_update.regions = [r.region for r in current_courier.regions]
    courier_update.working_hours = [TimeSegment.by_sums(ts.begin, ts.end) for ts in current_courier.working_hours]
    return courier_update


@app.route('/couriers', methods=['POST'])
def couriers_post():
    valid_couriers_json = []
    set_cour = set(c.id for c in db.session.query(CourierDB).all())
    not_valid = List_validation_error()
    try:
        tmp_list = json.loads(request.get_data())
    except:
        not_valid.additionalProp = ["error in parsing json by json.loads"]
        return not_valid.json(exclude_defaults=True), 400

    for courier_posted in tmp_list["data"]:
        try:
            courier_obj = CourierStrong.parse_obj(courier_posted)
            if courier_obj.id not in set_cour:
                valid_couriers_json.append(courier_obj)
                set_cour.add(courier_obj.id)
            else:
                not_valid.additionalProp.append(f"not uniq in service id {courier_obj.id}")
                not_valid.validation_error.couriers.append(Id(id=courier_posted["courier_id"]))
        except ValidationError as e:
            not_valid.additionalProp.append(str(e))
            not_valid.validation_error.couriers.append(Id(id=courier_posted["courier_id"]))

    if not_valid.validation_error.couriers:
        return not_valid.json(exclude_defaults=True), 400

    valid_requests = List_ids()

    for courier in valid_couriers_json:
        try:
            insert_courier(courier)
            valid_requests.couriers.append(Id(id=courier.id))
        except:
            not_valid.additionalProp.append(f"some sql error in {courier.id}")
            not_valid.validation_error.couriers.append(Id(id=courier.id))
    if not_valid.validation_error.couriers:
        return not_valid.json(exclude_defaults=True), 400
    return valid_requests.json(exclude_defaults=True), 201


@app.route('/couriers/<int:id>', methods=['PATCH'])
def couriers_patch(id):
    try:
        update_fields = CourierOptional.parse_raw(request.get_data())
        update_fields.id = id
        updated = update_db(update_fields)
    except Exception as e:
        return "{\"error\": \"required field to patch in courier_type , regions ,working_hours\"}", 400
    return updated.json()


@app.route('/orders', methods=['POST'])
def orders_post():
    valid_orders_json = []
    not_valid = List_validation_error()
    set_orders = set(o.id for o in db.session.query(OrderDB).all())
    try:
        tmp_list = json.loads(request.get_data())
    except:
        not_valid.additionalProp = ["error in parsing json by json.loads"]
        return not_valid.json(exclude_defaults=True), 400

    for order_posted in tmp_list["data"]:
        try:
            order_obj = Order.parse_obj(order_posted)
            if order_obj.id not in set_orders:
                valid_orders_json.append(order_obj)
                set_orders.add(order_obj.id)
            else:
                not_valid.additionalProp.append(f'not uniq order in system: id {order_obj.id}')
                not_valid.validation_error.orders.append(Id(id=order_posted["order_id"]))
        except ValidationError as e:
            not_valid.additionalProp.append(str(e))
            not_valid.validation_error.orders.append(Id(id=order_posted["order_id"]))

    if not_valid.validation_error.orders:
        return not_valid.json(exclude_defaults=True), 400

    valid_requests = List_ids()

    for order in valid_orders_json:
        try:
            insert_order(order)
            valid_requests.orders.append(Id(id=order.id))
        except Exception as e:
            not_valid.additionalProp.append(str(e))
            not_valid.validation_error.orders.append(Id(id=order.id))

    if not_valid.validation_error.orders:
        return not_valid.json(exclude_defaults=True), 400
    return valid_requests.json(exclude_defaults=True), 201


@app.route('/orders/assign', methods=['POST'])
def orders_assign_post():
    try:
        courier = CourierOptional.parse_raw(request.get_data())
        answer = assign_orders_to_courier(courier)
    except Exception as e:
        return f'{{ "error": {str(e)} }}', 400
    return answer, 200


@app.route('/orders/complete', methods=['POST'])
def orders_complete_post():
    try:
        order = Completed_order.parse_raw(request.get_data())
        insert_complete(order)
    except Exception as e:
        return f'{{ "error": {str(e)} }}', 400
    return f"{{ \"order_id\": {order.order_id} }}", 200


@app.route('/couriers/<int:id>', methods=['GET'])
def get_courier_data(id):
    try:
        return get_data(id)
    except Exception as e:
        return f'{{ "error": {str(e)} }}', 400


if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=True)
