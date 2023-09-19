import csv
import math
import random
from ..db import _db, Collections
from models.products import ProductBrands, Category, Product


# DATASET = "ecommerce_sample.csv"
DATASET = "/home/timileyin/Desktop/printing/lib/load_test_db/ecommerce_sample.csv"


def r_bool():
    return 50 > random.randint(0, 100)


async def load_data(n=100, only_category=True):
    i = 0

    brands = [item for item in dir(ProductBrands) if not item.startswith("_")]
    b_i = len(brands)

    with open(DATASET) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        # print("\n N -> ", len( [r for r in csv_reader]))

        for row in csv_reader:
            if i == 0:
                # print(f'Column names are {", ".join(row)}')
                pass

            else:
                # print(f'\t{row[0]} works in the {row[1]} department, and was born in {row[2]}.')
                # print( "\n\n ", i ," : ", brands[random.randint(0, b_i - 1) ] )

                image = row[-7]
                product_name = row[3]
                description = row[10]
                category_name = row[4]
                discount = random.randint(0, 90)
                brand = getattr(
                    ProductBrands, brands[random.randint(0, b_i - 1)])
                has_shipping = r_bool()
                has_free_shipping = r_bool() if has_shipping else False
                is_neg = r_bool()
                units = random.randint(10, 1000)
                max_units = random.randint(1, units - 1)

                if only_category:
                    nm = eval(category_name)[random.randint(
                        0, len(eval(category_name)) - 1)]
                    category = Category(
                        name=nm,
                        tags=[nm,],
                    )

                    await _db[Collections.productCategories].insert_one(category.dict())

                else:
                    cursor = _db[Collections.productCategories].find(
                        {}).sort("?")
                    categories = await cursor.to_list(length=math.ceil(n/4))
                    xr = random.randint(0, len(categories) - 4)
                    e_cats = [c["category_id"] for c in categories[xr: xr + 3]]

                    product = Product(

                        product_name=product_name,
                        description=description,
                        images_urls=eval(image),
                        thumbnail=eval(image)[0],
                        categories=e_cats,
                        brands=[brand, ],
                        units_in_stock=units,
                        max_units_per_buy=max_units,
                        price=float(random.randint(1000, 1000000)),
                        discount=discount,
                        has_shipping=has_shipping,
                        has_free_shipping=has_free_shipping,
                        is_negotiable=is_neg,
                        is_verified=is_neg

                    )

                    await _db[Collections.products].insert_one(product.dict())

            i += 1

            print("N: ", i, n)

            if i > n:
                break
