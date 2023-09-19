import math
from fastapi import HTTPException
from pydantic import BaseModel, EmailStr
from libs.config.settings import get_settings
from ..db import _db, Collections
from .pure_functions import get_utc_timestamp


settings = get_settings()


class Paginator:

    def __init__(self,  col_name:  Collections,  sort_field: str, top_down_sort: bool = True, filters: dict = {}, include_crumbs=True) -> None:
        self.per_page = settings.paginator_per_page
        self.sort_field = sort_field
        self.direction = -1 if top_down_sort else 1
        self.num_items = None
        self.include_crumbs = include_crumbs
        self.current_page = 1
        self.init = False
        self.col_name = col_name
        self.filters = filters
        self.query = None
        self.num_pages = None

    async def __initialize(self):
        if self.init:
            return

        self.init = True
        n = await _db[self.col_name].count_documents(self.filters)
        self.num_items = n

        self.query = _db[self.col_name].find(
            self.filters).sort(self.sort_field, self.direction)
        await self.get_num_pages()

    async def get_num_pages(self):

        if self.num_pages:
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

        if page > self.num_pages:
            raise HTTPException(
                400,  f"page exceeded number of pages ({page} > {self.num_pages})")

        if self.num_pages == 1:
            return await self.query.to_list(length=self.num_items)

        s_index = (self.per_page * page) - self.per_page

        e_index = min(s_index + self.per_page, self.num_items)

        return await self.query.skip(s_index).to_list(length=e_index - s_index)


async def has_next(self):

    return self.num_pages > self.current_page


async def has_prev(self):
    return self.current_page > 1


async def next_page(self):
    self.current_page += 1
    return await self.get_page(self.current_page)


async def prev_page(self):
    self.current_page -= 1
    return await self.get_page(self.current_page)


async def _validate_email_from_db(email:  EmailStr):
    existing = await _db[Collections.users].find_one({"email": email})

    if existing:
        return False
    else:
        return True


async def _validate_phone_from_db(phone:  str):
    existing = await _db[Collections.users].find_one({"phone": phone})

    if existing:
        return False
    else:
        return True


async def update_record(cls: BaseModel, data: dict,  col_name: Collections,  pk_name: str, update_last_write: bool = True, refresh_from_db: bool = False):

    if update_last_write:

        data.update({
            "updated_at": get_utc_timestamp()
        })

    await _db[col_name].update_one({pk_name: data[pk_name]}, {"$set": data})

    if not refresh_from_db:
        return cls(**data)

    else:

        updated_data = await _db[col_name].find_one({pk_name: data[pk_name]})

        return cls(**updated_data)


async def find_record(cls: BaseModel, col_name: Collections, pk_name: str,  pk: str, raise_404=True):

    record = await _db[col_name].find_one({pk_name: pk})

    if not record:
        if raise_404:
            raise HTTPException(
                404, f" {col_name.value} item with {pk_name} { pk } not found")
        else:
            return None

    else:

        return cls(**record)
