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
        "courier_type": "car",
        "regions": [
               1, 3
              ],
        "working_hours": [
               "00:00-12:00", "00:09-00:11"
        ]
        }
        """
        expected = {
            "error": 'id must be in system and required field to patch in courier_type , regions ,working_hours'
        }

        ans = requests.patch(self.adress + '/couriers/7', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        expected ={
                "courier_id": 4,
                "courier_type": "car",
                "regions": [
                    1,
                    3
                ],
                "working_hours": [
                    "00:00-12:00",
                    "00:09-00:11"
                ]
            }


        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)


    def test_logic(self):
        data = """
                {
                    "data": [ 
                            {
                        "courier_id": 4,
                        "courier_type": "car",
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
                            "order_id": 5,
                            "weight": 0.51,
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
                {"id": 5},
                {"id": 6},
                {"id": 7}
            ]
        }

        ans = requests.post(self.adress + '/orders', data=data)
        self.assertEqual(ans.status_code, 201)
        self.assertEqual(json.loads(ans.text), expected)

        data = '{"courier_id": 4}'
        ans = requests.post(self.adress + '/orders/assign', data=data)
        self.assertEqual(ans.status_code, 200)

        assign_time = json.loads(ans.text)["assign_time"]
        data = """
        {
            "courier_type": "car",
            "regions": [1],
            "working_hours": ["11:35-14:05", "09:00-11:00"]
        }
        """
        expected = {
            "courier_id": 4,
            "courier_type": "car",
            "regions": [1],
            "working_hours": ['09:00-11:00', '11:35-14:05']
        }
        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        expected = {
            "orders": [6]
        }

        ans = requests.post(self.adress + '/orders/assign', data='{"courier_id": 4}')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text)['orders'], expected['orders'])

        data = """
                {
                    "courier_type": "car",
                    "regions": [],
                    "working_hours": ["11:35-14:05", "09:00-11:00"]
                }
                """
        expected = {
            "orders": []
        }
        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)

        ans = requests.post(self.adress + '/orders/assign', data='{"courier_id": 4}')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
            {
                "courier_type": "car",
                "regions": [1, 12],
                "working_hours": ["21:35-22:05"]
            }
        """
        expected = {
            "orders": [5]
        }

        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)

        ans = requests.post(self.adress + '/orders/assign', data='{"courier_id": 4}')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text)['orders'], expected['orders'])

        data = """
                    {
                        "courier_type": "car",
                        "regions": [1, 12],
                        "working_hours": []
                    }
                """
        expected = {
            "orders": []
        }

        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)

        ans = requests.post(self.adress + '/orders/assign', data='{"courier_id": 4}')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
            {
                "courier_type": "car",
                "regions": [1, 12],
                "working_hours": ["00:00-23:59"]
            }
        """
        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)

        data = """
                    {
                        "courier_type": "foot",
                        "regions": [1, 12],
                        "working_hours": ["00:00-23:59"]
                    }
                """

        expected = {
            "orders": [1, 5]
        }
        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)

        ans = requests.post(self.adress + '/orders/assign', data='{"courier_id": 4}')
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text)['orders'], expected['orders'])

    def test_variable_fields(self):
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
                "courier_type": "foot"
                }
                """
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
            ]
        }
        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
        {
            "regions" : [99]
        }
        """
        expected = {
            "courier_id": 4,
            "courier_type": "foot",
            "regions": [99],
            "working_hours": [
                "09:00-11:00",
                "11:35-14:05"
            ]
        }
        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
                {
                    "working_hours": ["00:00-23:59"]
                }
                """
        expected = {
            "courier_id": 4,
            "courier_type": "foot",
            "regions": [99],
            "working_hours": ["00:00-23:59"]
        }
        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 200)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
        {
            "extra_field" : "miner"
        }
        """
        expected = {
          "error": "id must be in system and required field to patch in courier_type , regions ,working_hours"
        }
        ans = requests.patch(self.adress + '/couriers/4', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)


if __name__ == "__main__":
    unittest.main()