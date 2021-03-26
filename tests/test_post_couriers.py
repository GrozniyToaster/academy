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

    def test_simple_add(self):
        data = """
            {
                "data": [
                    {
                        "courier_id": 1,
                        "courier_type": "foot",
                        "regions": [
                            1,
                            12,
                            22
                        ],
                        "working_hours": [
                            "11:35-14:05",
                            "09:00-11:00"
                        ]
                    },
                    {
                        "courier_id": 2,
                        "courier_type": "bike",
                        "regions": [
                            22
                        ],
                        "working_hours": [
                            "09:00-18:00"
                        ]
                    },
                    {
                        "courier_id": 3,
                        "courier_type": "car",
                        "regions": [
                            12,
                            22,
                            23,
                            33
                        ],
                        "working_hours": []
                    }
                ]
            }
            """
        expected = {"couriers": [{"id": 1}, {"id": 2}, {"id": 3}]}
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 201)
        self.assertEqual(json.loads(ans.text), expected)


    def test_uniq_id(self):
        data = """
            {
                "data": [
                    {
                        "courier_id": 1,
                        "courier_type": "foot",
                        "regions": [
                            1,
                            12,
                            22
                        ],
                        "working_hours": [
                            "11:35-14:05",
                            "09:00-11:00"
                        ]
                    },
                    {
                        "courier_id": 1,
                        "courier_type": "bike",
                        "regions": [
                            22
                        ],
                        "working_hours": [
                            "09:00-18:00"
                        ]
                    },
                    {
                        "courier_id": 3,
                        "courier_type": "car",
                        "regions": [
                            12,
                            22,
                            23,
                            33
                        ],
                        "working_hours": []
                    }
                ]
            }
            """
        expected = {
            "validation_error": {
                "couriers": [
                    {"id": 1}
                ]
            },
            "additionalProp": [
                "not uniq in service id 1"
            ]
        }
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
            {
                "data": [
                    {
                        "courier_id": 3,
                        "courier_type": "car",
                        "regions": [
                            12,
                            22,
                            23,
                            33
                        ],
                        "working_hours": []
                    }
                ]
            }
            """
        expected = {"couriers": [{"id": 3}]}
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 201)
        self.assertEqual(json.loads(ans.text), expected)

        expected = expected = {
            "validation_error": {
                "couriers": [
                    {"id": 3}
                ]
            },
            "additionalProp": [
                "not uniq in service id 3"
            ]
        }
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

    def test_fields(self):
        data = """
            {
                "data": [
                    {
                        "courier_id": -1,
                        "courier_type": "car",
                        "regions": [
                            12,
                            22,
                            23,
                            33
                        ],
                        "working_hours": []
                    }
                ]
            }
            """
        expected = {
            "validation_error": {
                "couriers": [
                    {"id": -1}
                ]
            },
            "additionalProp": [
                "1 validation error for CourierStrong\ncourier_id\n  ensure this value is greater than 0 (type=value_error.number.not_gt; limit_value=0)"
            ]
        }
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
                    {
                        "data": [
                            {
                                "courier_id": 4,
                                "courier_type": "cat",
                                "regions": [
                                    1,
                                    12,
                                    22
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
            "validation_error": {
                "couriers": [
                    {
                        "id": 4
                    }
                ]
            },
            "additionalProp": [
                "1 validation error for CourierStrong\ncourier_type\n  unexpected value; permitted: 'foot', 'bike', 'car' (type=value_error.const; given=cat; permitted=('foot', 'bike', 'car'))"
            ]
        }
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
                {
                    "data": [
                        {
                            "courier_id": 4,
                            "courier_type": "car",
                            "regions": [
                                1,
                                12,
                                -1,
                                0
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
            "validation_error": {
                "couriers": [
                    {"id": 4}
                ]
            },
            "additionalProp": [
                "2 validation errors for CourierStrong\nregions -> 2\n  ensure this value is greater than 0 (type=value_error.number.not_gt; limit_value=0)\nregions -> 3\n  ensure this value is greater than 0 (type=value_error.number.not_gt; limit_value=0)"
            ]
        }
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
            {
                "data": [
                    {
                        "courier_id": 4,
                        "courier_type": "car",
                        "regions": [],
                        "working_hours": []
                    }
                ]
            }
         """
        expected = { "couriers": [ {"id": 4}]}
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 201)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
        {
            "data": [
                {
                    "courier_id": 4,
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
            "validation_error": {
                "couriers": [
                    {"id": 4}
                ]
            },
            "additionalProp": [
                "1 validation error for CourierStrong\ncourier_type\n  field required (type=value_error.missing)"
            ]
        }
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
        {
            "data": [
                {
                    "courier_id": 4,
                    "courier_type": "car",
                    "regions": [
                        1,
                        12
                    ],
                    "working_hours": [
                        "11:35-14:05",
                        "09:00-11:00"
                    ],
                    "come extra": 0
                }
            ]
        }
        """
        expected = {
            "validation_error": {
                "couriers": [
                    {"id": 4}
                ]
            },
            "additionalProp": [
                "1 validation error for CourierStrong\ncome extra\n  extra fields not permitted (type=value_error.extra)"
            ]
        }
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)

        data = """
        {
            "data": {
                "courier_id": 4,
                "courier_type": "car",
                "regions": [
                    1,
                    12,
                    -1,
                    0
                ],
                "working_hours": [
                    "11:35-14:05",
                    "09:00-11:00"
                ],
                "come extra"
            }
        ]
        }
        """
        expected = {
            "additionalProp": [
                "error in parsing json by json.loads"
            ]
        }
        ans = requests.post(self.adress + '/couriers', data=data)
        self.assertEqual(ans.status_code, 400)
        self.assertEqual(json.loads(ans.text), expected)







if __name__ == "__main__":
    unittest.main()