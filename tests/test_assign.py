import unittest
import json
import requests
from datetime import datetime

class CouriersPostTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.adress = 'http://localhost:8080'
        ans = requests.post(self.adress + '/clear', data='{"pass" : 4685}')
        self.assertEqual(ans.status_code, 200)

    def tearDown(self) -> None:
        ans = requests.post(self.adress + '/clear', data='{"pass" : 4685}')
        self.assertEqual(ans.status_code, 200)

    def test_simple(self):
        data = """
            {
                "data": [ 
                        {
                    "courier_id": 4,
                    "courier_type": "foot",
                    "regions": [
                        11,
                        12
                    ],
                    "working_hours": [
                        "11:35-14:05",
                        "09:00-11:00"
                    ]
                }
                ]

            }
            """
        expected = {
            "couriers": [
                {"id": 4}
            ]
        }

        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 201)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
                {
                    "data": [
                            {
                                    "order_id": 1,
                                    "weight": 0.01,
                                    "region": 12,
                                    "delivery_hours": ["11:05-13:25"]
                            },{
                                    "order_id": 2,
                                    "weight": 9.62,
                                    "region": 13,
                                    "delivery_hours": ["11:05-13:25"]
                            },{
                                    "order_id": 5,
                                    "weight": 9.51,
                                    "region": 12,
                                    "delivery_hours": ["00:00-23:59"]
                            },{
                                    "order_id": 6,
                                    "weight": 15.6,
                                    "region": 1,
                                    "delivery_hours": ["10:00-12:59"]
                            },{
                                    "order_id": 7,
                                    "weight": 14.5,
                                    "region": 1,
                                    "delivery_hours": ["00:00-00:15"]
                            }
                    ]
                }
                """
        expected = {
            "orders": [
                {"id": 1},
                {"id": 2},
                {"id": 5},
                {"id": 6},
                {"id": 7}
            ]
        }

        ans = requests.post(self.adress + '/orders', data=data)
        self.assertEqual(ans.status_code, 201)
        self.assertEqual(json.loads(ans.text), expected)

        data = '{"courier_id": 4}'
        expected ={
            "orders": [1, 5]
        }
        ans = requests.post(self.adress + '/orders/assign', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text)["orders"], expected["orders"])

        time = json.loads(ans.text)["assign_time"]

        ans = requests.post(self.adress + '/orders/assign', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text)["orders"], expected["orders"])

        data = f"""
        {{
            "courier_id": 4,
            "order_id": 5,
            "complete_time": "{datetime.utcnow()}"
        }}
        """
        expected = {
            "order_id": 5
        }
        ans = requests.post(self.adress + '/orders/complete', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        data = '{"courier_id": 4}'
        expected = {
            "orders": [1],
            "assign_time": time
        }
        ans = requests.post(self.adress + '/orders/assign', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        data = f"""
                {{
                    "courier_id": 4,
                    "order_id": 1,
                    "complete_time": "{datetime.utcnow()}"
                }}
                """
        expected = {
            "order_id": 1
        }
        ans = requests.post(self.adress + '/orders/complete', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        data = '{"courier_id": 4}'
        expected = {
            "orders": []
        }
        ans = requests.post(self.adress + '/orders/assign', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(expected, json.loads(ans.text))

        data = '{"courier_id": 7}'
        ans = requests.post(self.adress + '/orders/assign', data=data)
        self.assertEqual(ans.status_code, 400)

    def test_logic_update(self):
        data = """
            {
                "data": [ 
                        {
                    "courier_id": 4,
                    "courier_type": "foot",
                    "regions": [
                        1,
                        12
                    ],
                    "working_hours": [
                        "11:35-14:05",
                        "09:00-11:00"
                    ]
                }
                ]

            }
            """
        expected = {
            "couriers": [
                {"id": 4}
            ]
        }

        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 201)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
            {
                "data": [
                        {
                                "order_id": 1,
                                "weight": 0.01,
                                "region": 12,
                                "delivery_hours": ["11:05-13:25"]
                        },{
                                "order_id": 2,
                                "weight": 9.62,
                                "region": 12,
                                "delivery_hours": ["12:05-13:25"]
                        },{
                                "order_id": 5,
                                "weight": 9.63,
                                "region": 12,
                                "delivery_hours": ["00:00-23:59"]
                        },{
                                "order_id": 6,
                                "weight": 0.3,
                                "region": 1,
                                "delivery_hours": ["10:00-12:59"]
                        },{
                                "order_id": 7,
                                "weight": 14.5,
                                "region": 1,
                                "delivery_hours": ["00:00-00:15"]
                        }
                ]
            }
            """
        expected = {
            "orders": [
                {"id": 1},
                {"id": 2},
                {"id": 5},
                {"id": 6},
                {"id": 7}
            ]
        }

        ans = requests.post(self.adress + '/orders', data=data)
        self.assertEqual(ans.status_code, 201)
        self.assertEqual(json.loads(ans.text), expected)

        data = '{"courier_id": 4}'
        expected = {
            "orders": [1, 6, 2]
        }
        ans = requests.post(self.adress + '/orders/assign', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(expected["orders"], json.loads(ans.text)["orders"])

        time = json.loads(ans.text)["assign_time"]

        data = """
        {
            "working_hours": ["10:00-11:00"]
        }
        """
        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)

        expected = {
            "orders": [6],
            "assign_time": time
        }

        ans = requests.post(self.adress + '/orders/assign', data='{"courier_id": 4}')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(expected, json.loads(ans.text),)

        data = f"""{{
          "courier_id": 4,
          "order_id": 6,
          "complete_time": "{datetime.utcnow()}"
        }}
        """

        ans = requests.post(self.adress + '/orders/complete', data=data)
        self.assertEqual(ans.status_code, 200)

        expected = {
            "orders": [5]
        }

        ans = requests.post(self.adress + '/orders/assign', data='{"courier_id": 4}')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text)["orders"], expected["orders"])

        data = f"""{{
                  "courier_id": 4,
                  "order_id": 5,
                  "complete_time": "{datetime.utcnow()}"
                }}
                """

        ans = requests.post(self.adress + '/orders/complete', data=data)
        self.assertEqual(ans.status_code, 200)

        expected = {
            "orders": []
        }

        ans = requests.post(self.adress + '/orders/assign', data='{"courier_id": 4}')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)



if __name__ == "__main__":
    unittest.main()