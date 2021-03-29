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
        expected = {
            "orders": [{'id': 1}, {'id': 5}]
        }

        ans = requests.post(self.adress + '/orders/assign', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text)["orders"], expected["orders"])

        expected = {

            "courier_id": 4,
            "courier_type": "foot",
            "regions": [
                11,
                12
            ],
            "working_hours": [
                "09:00-11:00",
                "11:35-14:05"
            ],
            "earnings": 0

        }

        ans = requests.get(self.adress + '/couriers/4')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        ans = requests.get(self.adress + '/couriers/8')
        self.assertEqual(ans.status_code, 400)

        data = f"""
            {{
              "courier_id": 4,
              "order_id": 5,
              "complete_time": "{datetime.utcnow()}"
            }}
            """
        ans = requests.post(self.adress + '/orders/complete', data=data)
        self.assertEqual(ans.status_code, 200)

        ans = requests.get(self.adress + '/couriers/4')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        data = f"""
                    {{
                      "courier_id": 4,
                      "order_id": 1,
                      "complete_time": "{datetime.utcnow()}"
                    }}
                    """
        ans = requests.post(self.adress + '/orders/complete', data=data)
        self.assertEqual(ans.status_code, 200)

        ans = requests.get(self.adress + '/couriers/4')
        self.assertEqual(ans.status_code, 200)
        self.assertNotEqual(json.loads(ans.text), expected)









if __name__ == "__main__":
    unittest.main()