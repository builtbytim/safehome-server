import math
from libs.config.settings import get_settings
from pydantic_settings import SettingsConfigDict
from pydantic import BaseModel, Field
from typing import Any
from libs.db import Collections, _db


settings = get_settings()


class PaginatedResult(BaseModel):
    per_page: int = Field(ge=1, alias="perPage")
    num_items: int = Field(ge=0, alias="numItems")
    unfiltered_entries:  int | None = Field(ge=0, alias="unfilteredEntries")
    entries: int | None = Field(ge=0, )
    page: int = Field(ge=1)
    has_next: bool = Field(alias="hasNext")
    has_prev: bool = Field(alias="hasPrev")
    num_pages: int = Field(ge=0, alias="numPages")
    items: list[Any]

    model_config = SettingsConfigDict(populate_by_name=True)


class Paginator:

    def __init__(self,   col_name:  Collections,  sort_field: str, top_down_sort: bool = True, per_page: int = 2, filters: dict = {}, include_crumbs=True, filter_func=None,  root_filter: dict = {}) -> None:
        self.per_page = per_page
        self.sort_field = sort_field
        self.direction = -1 if top_down_sort else 1
        self.num_items = None
        self.entries = None
        self.unfiltered_entries = None
        self.include_crumbs = include_crumbs
        self.current_page = 1
        self.init = False
        self.col_name = col_name
        self.root_filter = root_filter

        if root_filter:
            self.filters = {**root_filter, **filters}

        else:
            self.filters = filters

        self.query = None
        self.num_pages = None
        self.filter_func = filter_func

    async def get_paginated_result(self, page: int, items_cls=None, exclude_fields=None):
        items = await self.get_page(page)
        mapped_items = [items_cls(**x).dict(by_alias=True, exclude=exclude_fields)
                        for x in items] if items_cls else items

        return PaginatedResult(
            has_next=await self.has_next(),
            has_prev=await self.has_prev(),
            num_pages=await self.get_num_pages(),
            num_items=len(items),
            per_page=self.per_page,
            page=page,
            items=mapped_items,
            entries=self.entries,
            unfiltered_entries=self.unfiltered_entries
        )

    async def __initialize(self):
        if self.init:
            return

        self.init = True

        self.unfiltered_entries = await _db[self.col_name].count_documents(self.root_filter)

        n = await _db[self.col_name].count_documents(self.filters)

        self.entries = n

        self.num_items = n

        self.query = _db[self.col_name].find(
            self.filters).sort(self.sort_field, self.direction)
        await self.get_num_pages()

    async def get_num_pages(self, refresh=False):

        if self.num_pages and not refresh:
            return self.num_pages

        await self.__initialize()
        n = math.floor(self.num_items/self.per_page)

        if self.num_items > (n * self.per_page) and self.include_crumbs:
            self.num_pages = n + 1
        else:
            self.num_pages = n

        return self.num_pages

    async def get_page(self, page: int):

        await self.__initialize()

        page = max(1, page)

        # if page > self.num_pages:
        #     raise HTTPException(
        #         400,  f"page exceeded number of pages ({page} > {self.num_pages})")

        if self.num_pages == 1 and page == 1 and not self.filter_func:
            return await self.query.to_list(length=self.num_items)

        if page > self.num_pages:
            self.current_page = page
            return {}

        s_index = (self.per_page * page) - self.per_page

        e_index = min(s_index + self.per_page, self.num_items)

        self.current_page = page

        page_items = await self.query.skip(s_index).to_list(length=e_index - s_index)

        if self.filter_func:

            filtered_items = []

            for item in page_items:
                if await self.filter_func(item):
                    filtered_items.append(item)

            page_items = filtered_items

            self.entries = len(page_items)
            self.num_items = len(page_items)
            await self.get_num_pages(refresh=True)

        return page_items

    async def has_next(self):
        if not self.init:
            await self.__initialize()

        return self.num_pages > self.current_page

    async def has_prev(self):
        if not self.init:
            await self.__initialize()

        return self.current_page > 1

    async def next_page(self):
        if not self.init:
            await self.__initialize()

        self.current_page += 1
        return await self.get_page(self.current_page)

    async def prev_page(self):
        if not self.init:
            await self.__initialize()

        self.current_page -= 1
        return await self.get_page(self.current_page)
