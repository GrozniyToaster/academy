import unittest
import json
import requests

class CouriersPostTestCase(unittest.TestCase):
    def setUp(self) -> None:
        self.adress = 'http://localhost:8080'
        ans = requests.post(self.adress + '/clear', data='{"pass" : 4685}')
        self.assertEqual(ans.status_code, 200)

    def tearDown(self) -> None:
        ans = requests.post(self.adress + '/clear', data='{"pass" : 4685}')
        self.assertEqual(ans.status_code, 200)

    def test_simple(self):
        data ="""
        {
            "data": [
                {
                    "order_id": 1,
                    "weight": 0.23,
                    "region": 12,
                    "delivery_hours": [
                        "09:00-18:00"
                    ]
                },
                {
                    "order_id": 2,
                    "weight": 15,
                    "region": 1,
                    "delivery_hours": [
                        "09:00-18:00"
                    ]
                },
                {
                    "order_id": 3,
                    "weight": 0.01,
                    "region": 22,
                    "delivery_hours": [
                        "09:00-12:00",
                        "16:00-21:30"
                    ]
                }
            ]
        }
        """
        expected = {
            "orders": [
                {"id": 1},
                {"id": 2},
                {"id": 3}
            ]
        }

        ans = requests.post(self.adress + '/orders', data=data)
        self.assertEqual(ans.status_code, 201)
        self.assertEqual(json.loads(ans.text), expected)

    def test_valid_fields(self):
        data = """
        {
            "data": [
                {
                    "order_id": 1,
                    "region": 0,
                    "delivery_hours": [
                        "09:00-18:00"
                    ]
                }
            ]
        }
        """
        expected = {
            "validation_error": {
                "orders": [
                    {"id": 1}
                ]
            },
            "additionalProp": [
                "2 validation errors for Order\nweight\n  field required (type=value_error.missing)\nregion\n  ensure this value is greater than 0 (type=value_error.number.not_gt; limit_value=0)"
            ]
        }

        ans = requests.post(self.adress + '/orders', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
                {
                    "data": [
                        {
                            "order_id": -1,
                            "region": 7,
                            "delivery_hours": [
                                "09:00-18:00"
                            ]
                        }
                    ]
                }
                """
        expected = {
            "validation_error": {
                "orders": [
                    {"id": -1}
                ]
            },
            "additionalProp": [
                "2 validation errors for Order\norder_id\n  ensure this value is greater than 0 (type=value_error.number.not_gt; limit_value=0)\nweight\n  field required (type=value_error.missing)"
            ]
        }

        ans = requests.post(self.adress + '/orders', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
        {
            "data": [
                {
                    "order_id": 1,
                    "weight": 59,
                    "region": 12,
                    "delivery_hours": [
                        "09:00-00:00"
                    ]
                }
            ]
        }
        """
        expected = {
            "validation_error": {
                "orders": [
                    {"id": 1}
                ]
            },
            "additionalProp": [
                "2 validation errors for Order\nweight\n  ensure this value is less than or equal to 50 (type=value_error.number.not_le; limit_value=50)\ndelivery_hours -> 0\n  Not valid time (type=value_error)"
            ]
        }

        ans = requests.post(self.adress + '/orders', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
        {
            "data": [
                {
                    "order_id": 1,
                    "weight": 0.01,
                    "region": 12,
                    "delivery_hours": []
                }
            ]
        }
                """
        expected = {
            "validation_error": {
                "orders": [
                    {"id": 1}
                ]
            },
            "additionalProp": [
                "1 validation error for Order\ndelivery_hours\n  ensure this value has at least 1 items (type=value_error.list.min_items; limit_value=1)"
            ]
        }

        ans = requests.post(self.adress + '/orders', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)





if __name__ == "__main__":
    unittest.main()