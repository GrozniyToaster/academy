from flask import Flask, request, abort
from pydantic import BaseModel, validator, ValidationError, Field
from typing import List, Literal, Optional
import re
import json

app = Flask(__name__)


class Time:
    def __init__(self, s: str = "00:00"):
        self.h, self.m = map(int, s.split(':'))
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
        return f"{self.begin}-{self.end}"


class Courier(BaseModel):
    id: int = Field(alias='courier_id')
    courier_type: Literal["foot", "bike", "car"]
    regions: List[int]
    working_hours: List[str]

    @validator('working_hours')
    def working_hours_is_valid(cls, list_times: List[str]):
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


class List_validation_error(BaseModel):
    validation_error: List_ids = List_ids()




def insert_in_table(table: str, some):
    if table == 'couriers':
        # do some
        return "done"


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

    print(not_valid.json(exclude_defaults=True))
    print(valid_couriers_json)
    valid_requests = List_ids()
    for courier in valid_couriers_json:
        try:
            insert_in_table('couriers', courier)
            valid_requests.couriers.append(Id(id=courier.id))
        except Exception:
            not_valid.validation_error.couriers.append(Id(id=courier.id))
    if not_valid.validation_error.couriers != []:
        return not_valid.json(exclude_defaults=True), 404
    return valid_requests.json(exclude_defaults=True)

if __name__ == '__main__':
    app.run()
