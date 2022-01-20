import inspect

import django
import pytest
from ninja import Schema

from ninja_extra import NinjaExtraAPI, api_controller, route
from ninja_extra.controllers import RouteFunction
from ninja_extra.pagination import (
    AsyncPaginatorOperation,
    PageNumberPagination,
    PageNumberPaginationExtra,
    PaginationBase,
    PaginatorOperation,
    paginate,
)
from ninja_extra.testing import TestAsyncClient, TestClient

ITEMS = list(range(100))


class CustomPagination(PaginationBase):
    # only offset param, defaults to 5 per page
    class Input(Schema):
        skip: int

    def paginate_queryset(self, items, request, **params):
        skip = params["pagination"].skip
        return items[skip : skip + 5]


@api_controller
class SomeAPIController:
    @route.get("/items_1")
    @paginate  # WITHOUT brackets (should use default pagination)
    def items_1(self, **kwargs):
        return ITEMS

    @route.get("/items_2")
    @paginate()  # with brackets (should use default pagination)
    def items_2(self, someparam: int = 0, **kwargs):
        # also having custom param `someparam` - that should not be lost
        return ITEMS

    @route.get("/items_3")
    @paginate(CustomPagination)
    def items_3(self, **kwargs):
        return ITEMS

    @route.get("/items_4")
    @paginate(PageNumberPaginationExtra, page_size=10)
    def items_4(self, **kwargs):
        return ITEMS

    @route.get("/items_5")
    @paginate(PageNumberPagination, page_size=10)
    def items_5_without_kwargs(self):
        return ITEMS


api = NinjaExtraAPI()
api.register_controllers(SomeAPIController)

client = TestClient(SomeAPIController)


class TestPagination:
    def test_paginator_operation_used(self):
        some_api_route_functions = {
            k: v
            for k, v in inspect.getmembers(
                SomeAPIController, lambda member: isinstance(member, RouteFunction)
            )
        }
        has_kwargs = ("items_1", "items_3", "items_4")
        for name, route_function in some_api_route_functions.items():
            assert hasattr(route_function.as_view, "paginator_operation")
            paginator_operation = route_function.as_view.paginator_operation
            assert isinstance(paginator_operation, PaginatorOperation)
            if name in has_kwargs:
                assert paginator_operation.view_func_has_kwargs

    def test_case1(self):
        response = client.get("/items_1?limit=10").json()
        assert response == ITEMS[:10]

        schema = api.get_openapi_schema()["paths"]["/api/items_1"]["get"]
        # print(schema)
        assert schema["parameters"] == [
            {
                "in": "query",
                "name": "limit",
                "schema": {
                    "title": "Limit",
                    "default": 100,
                    "exclusiveMinimum": 0,
                    "type": "integer",
                },
                "required": False,
            },
            {
                "in": "query",
                "name": "offset",
                "schema": {
                    "title": "Offset",
                    "default": 0,
                    "exclusiveMinimum": -1,
                    "type": "integer",
                },
                "required": False,
            },
        ]

    def test_case2(self):
        response = client.get("/items_2?limit=10").json()
        assert response == ITEMS[:10]

        schema = api.get_openapi_schema()["paths"]["/api/items_2"]["get"]
        # print(schema["parameters"])
        assert schema["parameters"] == [
            {
                "in": "query",
                "name": "someparam",
                "schema": {"title": "Someparam", "default": 0, "type": "integer"},
                "required": False,
            },
            {
                "in": "query",
                "name": "limit",
                "schema": {
                    "title": "Limit",
                    "default": 100,
                    "exclusiveMinimum": 0,
                    "type": "integer",
                },
                "required": False,
            },
            {
                "in": "query",
                "name": "offset",
                "schema": {
                    "title": "Offset",
                    "default": 0,
                    "exclusiveMinimum": -1,
                    "type": "integer",
                },
                "required": False,
            },
        ]

    def test_case3(self):
        response = client.get("/items_3?skip=5").json()
        assert response == ITEMS[5:10]

        schema = api.get_openapi_schema()["paths"]["/api/items_3"]["get"]
        # print(schema)
        assert schema["parameters"] == [
            {
                "in": "query",
                "name": "skip",
                "schema": {"title": "Skip", "type": "integer"},
                "required": True,
            }
        ]

    def test_case4(self):
        response = client.get("/items_4?page=2").json()
        assert response.get("results") == ITEMS[10:20]
        assert response.get("count") == 100
        assert response.get("next") == "http://testlocation/?page=3"
        assert response.get("previous") == "http://testlocation/"

        schema = api.get_openapi_schema()["paths"]["/api/items_4"]["get"]
        # print(schema)
        assert schema["parameters"] == [
            {
                "in": "query",
                "name": "page",
                "schema": {
                    "title": "Page",
                    "default": 1,
                    "exclusiveMinimum": 0,
                    "type": "integer",
                },
                "required": False,
            },
            {
                "in": "query",
                "name": "page_size",
                "schema": {
                    "title": "Page Size",
                    "default": 10,
                    "exclusiveMaximum": 200,
                    "type": "integer",
                },
                "required": False,
            },
        ]

    def test_case5(self):
        response = client.get("/items_5?page=2").json()
        assert response == ITEMS[10:20]

        schema = api.get_openapi_schema()["paths"]["/api/items_5"]["get"]
        # print(schema)
        assert schema["parameters"] == [
            {
                "in": "query",
                "name": "page",
                "schema": {
                    "title": "Page",
                    "default": 1,
                    "exclusiveMinimum": 0,
                    "type": "integer",
                },
                "required": False,
            }
        ]


@pytest.mark.skipif(django.VERSION < (3, 1), reason="requires django 3.1 or higher")
@pytest.mark.asyncio
class TestAsyncOperations:
    if not django.VERSION < (3, 1):

        @api_controller
        class AsyncSomeAPIController:
            @route.get("/items_1")
            @paginate  # WITHOUT brackets (should use default pagination)
            async def items_1(self, **kwargs):
                return ITEMS

            @route.get("/items_2")
            @paginate()  # with brackets (should use default pagination)
            async def items_2(self, someparam: int = 0, **kwargs):
                # also having custom param `someparam` - that should not be lost
                return ITEMS

            @route.get("/items_3")
            @paginate(CustomPagination)
            async def items_3(self, **kwargs):
                return ITEMS

            @route.get("/items_4")
            @paginate(PageNumberPaginationExtra, page_size=10)
            async def items_4(self, **kwargs):
                return ITEMS

            @route.get("/items_5")
            @paginate(PageNumberPagination, page_size=10)
            async def items_5_without_kwargs(self):
                return ITEMS

        api_async = NinjaExtraAPI()
        api_async.register_controllers(AsyncSomeAPIController)
        client = TestAsyncClient(AsyncSomeAPIController)

        async def test_paginator_operation_used(self):
            some_api_route_functions = {
                k: v
                for k, v in inspect.getmembers(
                    self.AsyncSomeAPIController,
                    lambda member: isinstance(member, RouteFunction),
                )
            }
            has_kwargs = ("items_1", "items_3", "items_4")
            for name, route_function in some_api_route_functions.items():
                assert hasattr(route_function.as_view, "paginator_operation")
                paginator_operation = route_function.as_view.paginator_operation
                assert isinstance(paginator_operation, AsyncPaginatorOperation)
                if name in has_kwargs:
                    assert paginator_operation.view_func_has_kwargs

        async def test_case1(self):
            response = await self.client.get("/items_1?limit=10")
            assert response.json() == ITEMS[:10]

            schema = self.api_async.get_openapi_schema()["paths"]["/api/items_1"]["get"]
            # print(schema)
            assert schema["parameters"] == [
                {
                    "in": "query",
                    "name": "limit",
                    "schema": {
                        "title": "Limit",
                        "default": 100,
                        "exclusiveMinimum": 0,
                        "type": "integer",
                    },
                    "required": False,
                },
                {
                    "in": "query",
                    "name": "offset",
                    "schema": {
                        "title": "Offset",
                        "default": 0,
                        "exclusiveMinimum": -1,
                        "type": "integer",
                    },
                    "required": False,
                },
            ]

        async def test_case2(self):
            response = await self.client.get("/items_2?limit=10")
            assert response.json() == ITEMS[:10]

        async def test_case3(self):
            response = await self.client.get("/items_3?skip=5")
            assert response.json() == ITEMS[5:10]

        async def test_case4(self):
            response = await self.client.get("/items_4?page=2")
            response = response.json()
            assert response.get("results") == ITEMS[10:20]
            assert response.get("count") == 100
            assert response.get("next") == "http://testlocation/?page=3"
            assert response.get("previous") == "http://testlocation/"

        async def test_case5(self):
            response = await self.client.get("/items_5?page=2")
            assert response.json() == ITEMS[10:20]
