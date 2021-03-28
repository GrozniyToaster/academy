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


def recalculate_rating(id: int, type_last_pack: str):
    courier = db.session.query(CourierDB).filter_by(id=id).one()
    if courier.count_completed_orders_in_pack == 0:
        return
    ranges = db.session.query(Rating).filter_by(id=id).all()
    t = float('inf')
    for r in ranges:
        t = min(t, r.sum_dt / r.count_orders)
    courier.rating = round((60 * 60 - min(t, 60 * 60)) / (60 * 60) * 5, 2)
    courier.earnings += 500 * payment_c[type_last_pack]
    courier.count_completed_orders_in_pack = 0
    db.session.commit()


def get_data(id: int):
    cDB = db.session.query(CourierDB).filter_by(id=id).one()
    rating, payment = cDB.rating, cDB.earnings
    ans = CourierOptional()
    ans.id = id
    ans.type = cDB.type
    ans.regions = [r.region for r in cDB.regions]
    ans.working_hours = [TimeSegment.by_sums(wh.begin, wh.end) for wh in cDB.working_hours]
    if rating != -1:
        ans.rating = rating
    ans.earnings = payment
    return ans.json(exclude_defaults=True, by_alias=True)


def insert_courier(c: CourierStrong):
    courier = CourierDB(id=c.id, type=c.type, count_completed_orders_in_pack=0, earnings=0, rating=-1)
    courier.regions = [
        CourierRegion(region=r) for r in c.regions
    ]
    courier.working_hours = [
        CourierWorkingHours(begin=wh.begin.sum, end=wh.end.sum) for wh in c.working_hours
    ]
    db.session.add(courier)
    try:
        db.session.commit()
    except Exception as e:
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


def update_rating_fields(courier_id, order_id, region, dt, type):
    try:
        rec = db.session.query(Rating).filter_by(id=courier_id, region=region).one()
        rec.sum_dt += round(dt.total_seconds())

    except:
        rec = Rating(id=courier_id, region=region, sum_dt=round(dt.total_seconds()),
                     count_orders=0)
        db.session.add(rec)
    rec.count_orders += 1
    db.session.commit()


def insert_complete(o: Completed_order):
    cur_o = db.session.query(OrderDB).filter_by(id=o.order_id).one()
    if cur_o.completed:
        return
    cur_rec = db.session.query(Assigned_Order).filter_by(id_order=o.order_id, id_courier=o.courier_id).one()
    cur_cour = db.session.query(CourierDB).filter_by(id=o.courier_id).one()
    cur_cour.count_completed_orders_in_pack += 1
    update_rating_fields(o.courier_id,
                         o.order_id,
                         cur_o.region,
                         o.complete_time.replace(tzinfo=None) - cur_rec.courier.time_last_order,
                         cur_rec.type
                         )

    type_pack = cur_rec.type
    cur_o.completed = True
    cur_rec.courier.time_last_order = o.complete_time
    db.session.query(Assigned_Order).filter_by(id_order=o.order_id, id_courier=o.courier_id).delete()
    db.session.commit()
    if cur_cour.assigned == []:
        recalculate_rating(o.courier_id, type_pack)


def intersection_segments(a1, b1, a2, b2):
    return (b2 > a1 and a2 < b1)


def segregate(b, e):
    time = []
    if b < e:
        if b < e:
            time.append([b, e])
    else:
        if b != 23 * 60 + 59:
            time.append([b, 23 * 60 + 59])
        if e != 0:
            time.append([0, e])
    return time


def intersection_times(b1, e1, b2, e2):
    time1 = segregate(b1, e1)
    time2 = segregate(b2, e2)
    for [a, b] in time1:
        for [c, d] in time2:
            if intersection_segments(a, b, c, d):
                return True
    return False


def get_max_orders(orders, cap):
    n = len(orders)
    c = generate_zero_matrix(n, cap + 1)
    for i in range(0, n):
        for j in range(0, cap + 1):
            if (orders[i] > j):
                c[i][j] = c[i - 1][j]
            else:
                c[i][j] = max(c[i - 1][j], orders[i] + c[i - 1][j - orders[i]])
    return [c[n - 1][cap], to_bit_mask(orders, c)]


def generate_zero_matrix(x, y):
    row = []
    data = []
    for i in range(y):
        row.append(0)
    for i in range(x):
        data.append(row[:])
    return data


def to_bit_mask(w, c):
    i = len(c) - 1
    curW = len(c[0]) - 1
    mask = []
    for i in range(i + 1):
        mask.append(0)
    while (i >= 0 and curW >= 0):
        if (i == 0 and c[i][curW] > 0) or c[i][curW] != c[i - 1][curW]:
            mask[i] = 1
            curW = curW - w[i]
        i = i - 1
    return mask


def choose_orders(valid_orders: List[OrderDB], cap: int):
    if not valid_orders:
        return []
    orders_weight = [int(round(o.weight * 100)) for o in valid_orders]
    max_size, packed = get_max_orders(orders_weight, cap * 100)
    id_to_get = []
    for i in range(len(packed)):
        if packed[i]:
            id_to_get.append(valid_orders[i].id)
    return id_to_get


def import_data_from_db(courier: CourierOptional):
    courier_db = db.session.query(CourierDB).filter_by(id=courier.id).one()
    regions = [r.region for r in courier_db.regions]
    capacity = lifting_capacity[courier_db.type]

    vocant_orders = db.session.query(OrderDB).filter(
        and_(text(f'orders_completed = False AND orders_weight <= {capacity}'),
             OrderDB.region.in_(regions))
    ).order_by(OrderDB.weight).all()

    not_packed_orders = []
    for order in vocant_orders:
        if order.assigned:
            continue
        added = False
        for dh in order.delivery_hours:
            if added:
                break
            for wh in courier_db.working_hours:
                if added:
                    break
                if intersection_times(wh.begin, wh.end, dh.begin, dh.end):
                    not_packed_orders.append(order)
                    added = True

    orders_to_assign = choose_orders(not_packed_orders, capacity)

    return orders_to_assign, courier_db


def add_rec_assigned_order(orders: List[int], courier: CourierDB):
    if orders:
        time = datetime.utcnow()
        courier.assigned = [
            Assigned_Order(id_order=oid, time=time, type=courier.type) for oid in orders
        ]
        courier.time_last_order = time
        db.session.commit()
        ans = List_ids()
        ans.orders = list(map(lambda x: Id(id=x), orders))
        ans.assign_time = courier.assigned[0].time
        ans = ans.json(exclude_defaults=True, by_alias=True)
    else:
        ans = "{\"orders\": []}"

    return ans


def assign_orders_to_courier(courier: CourierOptional):
    # checkin order availability
    orders = db.session.query(Assigned_Order).filter_by(id_courier=courier.id).all()
    if orders:
        ans = List_ids()
        ans.orders = [Id(id=order.id_order) for order in orders]
        ans.assign_time = orders[0].time
        return ans.json(exclude_defaults=True, by_alias=True)

    orders, courier_db = import_data_from_db(courier)
    return add_rec_assigned_order(orders, courier_db)


def correct_assigned_orders(c: CourierOptional):
    orders = db.session.query(Assigned_Order).filter_by(
        id_courier=c.id
    ).all()
    if not orders:
        return
    capacity = lifting_capacity[c.type]
    pack_type = orders[0].type
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
    db.session.commit()

    orders = db.session.query(Assigned_Order).filter_by(
        id_courier=c.id
    ).all()
    if not orders:
        recalculate_rating(c.id, pack_type)
        return

    orders_to_func = [OrderDB(id=o.id_order, weight=o.order.weight, region=42) for o in orders]

    id_chosen = choose_orders(orders_to_func, capacity)
    for o in orders:
        if o.id_order not in id_chosen:
            db.session.query(Assigned_Order).filter_by(id_order=o.id_order).delete()
    db.session.commit()
    if not db.session.query(Assigned_Order).filter_by(id_courier=c.id).all():
        recalculate_rating(c.id, pack_type)


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
    # forming answer and deprecate not valid orders
    courier_update.type = current_courier.type
    courier_update.regions = [r.region for r in current_courier.regions]
    courier_update.working_hours = [TimeSegment.by_sums(ts.begin, ts.end) for ts in current_courier.working_hours]
    correct_assigned_orders(courier_update)

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
    return valid_requests.json(exclude_defaults=True, by_alias=True), 201


@app.route('/couriers/<int:id>', methods=['PATCH'])
def couriers_patch(id):
    try:
        update_fields = CourierOptional.parse_raw(request.get_data())
        update_fields.id = id
        updated = update_db(update_fields)
    except Exception as e:
        return "{\"error\": \"id must be in system and required field to patch in courier_type , regions ,working_hours\"}", 400
    return updated.json(exclude_defaults=True, by_alias=True), 200


@app.route('/orders', methods=['POST'], strict_slashes=False)
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
    return valid_requests.json(exclude_defaults=True, by_alias=True), 201


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


@app.route('/clear', methods=['POST'])
def clear():
    rec = json.loads(request.get_data())
    if rec['pass'] != 4685:
        return "", 404
    db.drop_all()
    db.create_all()
    return '', 200


if __name__ == '__main__':
    db.create_all()
    app.run(host="0.0.0.0", port=8080)
