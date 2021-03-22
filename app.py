from flask import request
from pydantic import ValidationError
from ValidatorModels import Courier, Completed_order, Order, List_ids, List_validation_error, TimeSegment, Id

from ModelsDB import app, db, CourierDB, CourierWorkingHours, CourierRegion, OrderDB, OrdersDeliveryHours, \
    Assigned_Order

import json

lifting_capacity = {
    'foot': 10,
    'bike': 15,
    'car': 50
}

def get_data(id: int):
    cDB = db.session.query(CourierDB).filter_by(id=id).one()
    ans = Courier()
    ans.id = id
    ans.type = cDB.type
    ans.regions = [r.region for r in cDB.regions]
    ans.working_hours = [TimeSegment.by_sums(wh.begin, wh.end) for wh in cDB.working_hours]
    return ans.json()
def insert_courier(c: Courier):
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

def recalculate_reiting(courier_id, order_id, region, dt):
    print(dt)
    pass


def insert_complete(o: Completed_order):
    cur_rec = db.session.query(Assigned_Order).filter_by(id_order=o.order_id, id_courier=o.courier_id).one()
    cur_o = db.session.query(OrderDB).filter_by(id=o.order_id).one()
    recalculate_reiting(o.courier_id, o.order_id, cur_o.region,
                        o.complete_time.replace(tzinfo=None) - cur_rec.time.replace(tzinfo=None)
                        )
    db.session.query(OrderDB).filter_by(id=o.order_id).delete()
    db.session.query(Assigned_Order).filter_by(id_order=o.order_id, id_courier=o.courier_id).delete()
    db.session.commit()



def import_data_from_db(courier: Courier):
    courier_db = db.session.query(CourierDB).filter_by(id=courier.id).one()
    regions = [r.region for r in courier_db.regions]
    capacity = lifting_capacity[courier_db.type]
    vocant_orders = []
    for r in regions:
        vocant_orders.append(db.session.query(OrderDB).filter(OrderDB.region == r).all())

    not_sorted_orders = []
    not_sorted_working_hours = []
    for group_region in vocant_orders:
        for order in group_region:
            if order.weight <= capacity and db.session.query(Assigned_Order).filter_by(id_order=order.id).all() == []:
                for dh in order.delivery_hours:
                    not_sorted_orders.append([dh.begin, dh.end, order.id])
    for wh in courier_db.working_hours:
        not_sorted_working_hours.append([wh.begin, wh.end])
    sorted_workig_hours = sorted(not_sorted_working_hours, key=lambda x: x[0])
    sorted_times_order = sorted(not_sorted_orders, key=lambda x: x[0])
    return sorted_times_order, sorted_workig_hours, courier_db


def choose_orders(times_order, working_hours):
    orders = []
    size_of_orders = len(times_order)
    cur_i = 0
    for wbegin, wend in working_hours:
        while cur_i < size_of_orders and times_order[cur_i][0] < wbegin:
            cur_i += 1
        cur_end_of_order = wbegin

        while cur_i < size_of_orders and times_order[cur_i][0] < wend:
            if cur_end_of_order <= times_order[cur_i][0] and \
                    times_order[cur_i][1] <= wend:  # если не выполняем заказов и успеем в нашу смену
                if times_order[cur_i][2] not in orders:
                    orders.append(times_order[cur_i][2])  # берем новый заказ
                    cur_end_of_order = times_order[cur_i][1]  # запоминаем когда закончится
            else:
                if cur_end_of_order >= times_order[cur_i][1]:  # если текущий заказ закончится позже
                    if times_order[cur_i][2] not in orders:
                        orders[-1] = times_order[cur_i][2]  # берем тот который выполнить быстрее
                        cur_end_of_order = times_order[cur_i][1]  # запоминаем когда закончится
            cur_i += 1
    return list(set(orders))


def assign_orders_to_courier(courier: Courier):
    # checkin order availability
    orders = db.session.query(Assigned_Order).filter_by(id_courier=courier.id).all()
    if orders:
        ans = List_ids()
        ans.orders = [order.id_order for order in orders]
        ans.assign_time = orders[0].time
        return ans.json(exclude_defaults=True)

    times_order, working_hours, courier_db = import_data_from_db(courier)
    orders = choose_orders(times_order, working_hours)

    if orders:
        courier_db.assigned = [
            Assigned_Order(id_order=oid) for oid in orders
        ]
        db.session.commit()
        ans = List_ids()
        ans.orders = orders
        ans.assign_time = courier_db.assigned[0].time
        ans = ans.json(exclude_defaults=True)
    else:
        ans = "{\"orders\": []}"

    return ans


def correct_assigned_orders(c: Courier):
    orders = db.session.query(Assigned_Order).filter_by(id_courier=c.id).all()
    capacity = lifting_capacity[c.type]
    for order in orders:
        if order.order.weight > capacity or order.order.region not in c.regions:
            db.session.query(Assigned_Order).filter_by(id_order=order.id_order).delete()
    db.session.commit()


def update_db(courier_update: Courier):
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
    tmp_list = json.loads(request.get_data())
    valid_couriers_json = []
    not_valid = List_validation_error()

    for courier_posted in tmp_list["data"]:
        try:
            courier_obj = Courier.parse_obj(courier_posted)
            valid_couriers_json.append(courier_obj)
        except ValidationError as e:
            not_valid.validation_error.couriers.append(Id(id=courier_posted["courier_id"]))

    if not_valid.validation_error.couriers != []:
        return not_valid.json(exclude_defaults=True), 400

    valid_requests = List_ids()

    for courier in valid_couriers_json:
        try:
            insert_courier(courier)
            valid_requests.couriers.append(Id(id=courier.id))
        except:
            not_valid.validation_error.couriers.append(Id(id=courier.id))
    if not_valid.validation_error.couriers != []:
        return not_valid.json(exclude_defaults=True), 400
    return valid_requests.json(exclude_defaults=True), 200


@app.route('/couriers/<int:id>', methods=['PATCH'])
def couriers_patch(id):
    try:
        update_fields = Courier.parse_raw(request.get_data())
        update_fields.id = id
        updated = update_db(update_fields)
    except Exception as e:
        return "Bad data", 400
    return updated.json()


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

    if not_valid.validation_error.orders != []:
        return not_valid.json(exclude_defaults=True), 400

    valid_requests = List_ids()

    for order in valid_orders_json:
        try:
            insert_order(order)
            valid_requests.orders.append(Id(id=order.id))
        except Exception as e:
            not_valid.validation_error.orders.append(Id(id=order.id))

    if not_valid.validation_error.orders != []:
        return not_valid.json(exclude_defaults=True), 400
    return valid_requests.json(exclude_defaults=True), 200


@app.route('/orders/assign', methods=['POST'])
def orders_assign_post():
    try:
        courier = Courier.parse_raw(request.get_data())
        answer = assign_orders_to_courier(courier)
    except Exception as e:
        return "Bad Data", 400
    return answer


@app.route('/orders/complete', methods=['POST'])
def orders_complete_post():
    try:
        order = Completed_order.parse_raw(request.get_data())
        insert_complete(order)
    except Exception as e:
        return "Bad value", 400
    return f"{{ \"order_id\": {order.order_id} }}", 200


@app.route('/couriers/<int:id>', methods=['GET'])
def get_courier_data(id):
    try:

        return get_data(id)
    except Exception as e:
        return "[]", 400


if __name__ == '__main__':
    app.run(host="localhost", port=8080, debug=True)
