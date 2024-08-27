import xmlrpc.client
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional

# Configura los detalles de la conexión a Odoo
url = 'https://symtechven1.odoo.com/'
db = 'symtechven1'
username = 'escalonaf12@gmail.com'
password = 'Link420/'

# Conectar al servidor
common = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/common', allow_none=True)
uid = common.authenticate(db, username, password, {})

# Crear un cliente para los métodos de objetos
models = xmlrpc.client.ServerProxy(f'{url}/xmlrpc/2/object', allow_none=True)

# Inicializar FastAPI
app = FastAPI()
class QuantityUpdate(BaseModel):
    qty_available: float

# Modelo de datos para FastAPI, incluyendo el ID
class Product(BaseModel):
    barcode: Optional[str] = None
    name: str
    price: float
    description: Optional[str] = None
    quantity_svl: float
    is_storable: bool
    quantity_on_hand: float
    qty_available: float
class ProductCreate(BaseModel):
    barcode: Optional[str] = None
    name: str
    price: float
    description: Optional[str] = None
    quantity_svl: float
    is_storable: bool = True





@app.post("/products/")
async def create_product(product: ProductCreate):
    if product.barcode:
        existing_product_ids = models.execute_kw(
            db, uid, password,
            'product.product', 'search',
            [[('barcode', '=', product.barcode)]]
        )
        if existing_product_ids:
            raise HTTPException(status_code=400, detail=f"Barcode '{product.barcode}' already assigned to another product.")

    product_id = models.execute_kw(
        db, uid, password,
        'product.product', 'create',
        [{
            'barcode': product.barcode,
            'name': product.name,
            'list_price': product.price,
            'description_sale': product.description,
            'is_storable': product.is_storable
        }]
    )

    if product.quantity_svl > 0:
        stock_location = models.execute_kw(
            db, uid, password,
            'stock.location', 'search',
            [[('usage', '=', 'internal')]],
            {'limit': 1}
        )

        if stock_location:
            inventory_adjustment = models.execute_kw(
                db, uid, password,
                'stock.quant', 'create',
                [{
                    'product_id': product_id,
                    'location_id': stock_location[0],
                    'inventory_quantity': product.quantity_svl
                }]
            )

            models.execute_kw(
                db, uid, password,
                'stock.quant', 'action_apply_inventory',
                [inventory_adjustment]
            )

    product_details = models.execute_kw(
        db, uid, password,
        'product.product', 'read',
        [[product_id]],
        {'fields': ['name', 'list_price', 'description_sale', 'barcode', 'quantity_svl', 'qty_available']}
    )

    if not product_details:
        raise HTTPException(status_code=404, detail="Product details could not be fetched")

    return "Product created successfully"

@app.put("/products/{barcode}/quantity")
async def update_product_quantity(barcode: str, quantity_update: QuantityUpdate):
    product_ids = models.execute_kw(
        db, uid, password,
        'product.product', 'search',
        [[('barcode', '=', barcode)]]
    )
    if not product_ids:
        raise HTTPException(status_code=404, detail="Product not found")

    product_id = product_ids[0]

    stock_location = models.execute_kw(
        db, uid, password,
        'stock.location', 'search',
        [[('usage', '=', 'internal')]],
        {'limit': 1}
    )

    if stock_location:
        inventory_adjustment = models.execute_kw(
            db, uid, password,
            'stock.quant', 'create',
            [{
                'product_id': product_id,
                'location_id': stock_location[0],
                'inventory_quantity': quantity_update.qty_available
            }]
        )

        models.execute_kw(
            db, uid, password,
            'stock.quant', 'action_apply_inventory',
            [inventory_adjustment]
        )

    return {"detail": "Product quantity updated successfully"}
# Update the get_products endpoint
@app.get("/products/")
async def get_products():
    product_ids = models.execute_kw(
        db, uid, password,
        'product.product', 'search',
        [[]]
    )
    products = models.execute_kw(
        db, uid, password,
        'product.product', 'read',
        [product_ids],
        {'fields': ['name', 'list_price', 'description_sale', 'barcode', 'quantity_svl', 'qty_available']}
    )
    return [
        {
            "barcode": p['barcode'] if isinstance(p['barcode'], str) else None,
            "name": p['name'],
            "price": p['list_price'],
            "description": p.get('description_sale', '') if p.get('description_sale') else "",
            "quantity_svl": p['quantity_svl'],
            "quantity_on_hand": p['quantity_svl'],  # Assuming quantity_svl is the quantity on hand
            "qty_available": p['qty_available']
        }
        for p in products
    ]


@app.get("/products/{barcode}")
async def get_product(barcode: str):
    product_ids = models.execute_kw(
        db, uid, password,
        'product.product', 'search',
        [[('barcode', '=', barcode)]]
    )
    if not product_ids:
        raise HTTPException(status_code=404, detail="Product not found")

    products = models.execute_kw(
        db, uid, password,
        'product.product', 'read',
        [product_ids],
        {'fields': ['name', 'list_price', 'description_sale', 'barcode', 'quantity_svl', 'qty_available']}
    )
    product = products[0]
    product['quantity_on_hand'] = product['quantity_svl']  # Assuming quantity_svl is the quantity on hand
    return product