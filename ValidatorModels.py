from pydantic import BaseModel, validator, ValidationError, Field, confloat, conint, conlist
from typing import List, Literal, Optional
import re
from datetime import datetime

time_template = re.compile(r'^\d{2}:\d{2}-\d{2}:\d{2}$')

class Time:
    def __init__(self, s: str = "00:00"):
        self.h, self.m = map(int, s.split(':'))
        assert 0 <= self.h <= 24 and 0 <= self.m <= 60  # check valid time
        self.sum = self.h * 60 + self.m

    @classmethod
    def from_sum(cls, sum: int):
        if not isinstance(sum, int):
            raise ValueError("Not valid time")
        if sum > 1439 or sum < 0:  # 23:59 in minutes
            raise ValueError(f"{sum} > 23:59 in minutes or {sum} < 0")
        obj = cls()
        obj.sum = sum
        obj.h = sum // 60
        obj.m = sum % 60
        return obj

    def __str__(self):
        return f"{self.h:02d}:{self.m:02d}"

    def __repr__(self):
        return f"Time({str(self)})"


class TimeSegment:
    def __init__(self, seg: str = "00:00-00:01"):
        times = re.findall(time_template, seg)
        if not times:
            raise ValueError("Not valid time")
        begin, end = (times[0]).split('-')
        self.begin = Time(begin)
        self.end = Time(end)
        if self.begin.sum >= self.end.sum:  # если конец раньше чем начало данные не валидны
            raise ValueError("Not valid time")

    @classmethod
    def by_sums(cls, s1, s2):
        if s1 >= s2:
            raise ValueError("Not valid time")
        obj = cls()
        obj.begin = Time.from_sum(s1)
        obj.end = Time.from_sum(s2)
        return obj

    def __str__(self):
        return f"{self.begin}-{self.end}"

    @classmethod
    def validate(cls, v):
        if not isinstance(v, str):
            raise ValueError(f'str expected, got {type(v)}')
        return cls(v)

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    def __repr__(self):
        return f"TimeSegment({self.begin}-{self.end})"

class CourierStrong(BaseModel):
    id: conint(gt=0) = Field(alias='courier_id')
    type: Literal["foot", "bike", "car"] = Field(alias='courier_type')
    regions: List[conint(gt=0)]
    working_hours: List[TimeSegment]

    class Config:
        extra = 'forbid'
        json_encoders = {
            TimeSegment: lambda v: str(v)
        }


class CourierOptional(BaseModel):
    id: Optional[conint(gt=0)] = Field(alias='courier_id')
    type: Optional[Literal["foot", "bike", "car"]] = Field(alias='courier_type')
    regions: Optional[List[conint(gt=0)]] = None
    working_hours: Optional[List[TimeSegment]]
    rating: Optional[float] = None
    earnings: Optional[int] = None

    class Config:
        extra = 'forbid'
        json_encoders = {
            TimeSegment: lambda v: str(v)
        }


class Order(BaseModel):
    id: conint(gt=0) = Field(alias='order_id')
    weight: confloat(ge=0.01, le=50)
    region: conint(gt=0)
    delivery_hours: conlist(TimeSegment, min_items=1)

    @validator('weight')
    def two_numbers_after_dot(cls, v):
        return round(v, 2)

    class Config:
        extra = 'forbid'
        json_encoders = {
            TimeSegment: lambda v: str(v),

        }



class Id(BaseModel):
    id: int


class List_ids(BaseModel):
    couriers: Optional[List[Id]] = []
    orders: Optional[List[Id]] = []
    assign_time: Optional[datetime] = None

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
        }


class List_validation_error(BaseModel):
    validation_error: List_ids = List_ids()
    additionalProp: Optional[List[str]] = []


class Completed_order(BaseModel):
    courier_id: conint(gt=0)
    order_id: conint(gt=0)
    complete_time: datetime

    class Config:
        json_encoders = {
            datetime: lambda v: v.strftime('%Y-%m-%dT%H:%M:%S.%fZ'),

        }


