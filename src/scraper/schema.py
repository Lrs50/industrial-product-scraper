from typing import Dict, Any,List,Union
from collections import defaultdict
from pydantic import BaseModel

from utils import *

class Product(BaseModel):
    product_id: str
    name: str = None
    description: str = None
    brand: str = None
    category: str = None
    status: str 
    price_usd: str = None

    info: Dict[str, str] = None
    specs: Dict[str, str] = None
    bom: List[Dict[str, str]] = None
    accessories: List[Dict[str, str]] = None
    nameplate: Dict[str, Union[str, List[str]]] = None
    assets: Dict[str, Union[str, List[str]]] = None

def deduplicate_bom(bom: List[Dict[str, str]]) -> List[Dict[str, str]]:
    """
    Deduplicates BOM items by summing their quantities per part_number.

    Args:
        bom (List[Dict[str, str]]): Original BOM list, possibly with repeated parts.

    Returns:
        List[Dict[str, str]]: Deduplicated BOM list with quantities summed as strings (e.g., "3.000 EA").
    """
    grouped = defaultdict(lambda: {"description": "", "quantity": 0.0})

    for item in bom:
        part_number = item.get("part_number")
        description = item.get("description", "")
        qty_raw = item.get("quantity", "0")

        try:
            qty_val = float(qty_raw.split()[0])  # handles "1.000 EA", etc
        except (ValueError, IndexError):
            qty_val = 0.0

        grouped[part_number]["description"] = description
        grouped[part_number]["quantity"] += qty_val

    deduped_bom = []
    for part_number, data in grouped.items():
        deduped_bom.append({
            "part_number": part_number,
            "description": data["description"],
            "quantity": f"{data['quantity']:.3f} EA"
        })

    return deduped_bom

def remove_empty_fields(data: Any) -> Any:

    """
    Recursively removes empty or null values from a nested dictionary or list structure.

    This function is typically used to clean JSON-like objects by removing keys or elements
    with values considered empty (i.e., None, empty string, empty list, or empty dict),
    resulting in a cleaner and more compact data representation.

    Args:
        data (Any): A JSON-like structure (dictionary, list, or primitive type) to be cleaned.

    Returns:
        Any: The same structure with all empty fields removed. 
             Dictionaries and lists are returned recursively cleaned, and primitives are returned as-is.
    """

    # Case 1: If it's a dictionary, process each key-value pair
    if isinstance(data, dict):
        cleaned = {}
        for key, value in data.items():
            cleaned_value = remove_empty_fields(value)
            if cleaned_value not in [None, "", [], {}]:
                cleaned[key] = cleaned_value
        return cleaned

    # Case 2: If it's a list, process each item
    elif isinstance(data, list):
        cleaned_list = []
        for item in data:
            cleaned_item = remove_empty_fields(item)
            if cleaned_item not in [None, "", [], {}]:
                cleaned_list.append(cleaned_item)
        return cleaned_list

    # Case 3: If it's a primitive value (str, int, etc), return as-is
    else:
        return data

def get_attribute(attributes: List[Dict[str, Any]], name: str) -> str:
    for attr in attributes:
        if attr.get("name") == name and attr.get("values"):
            return attr["values"][0].get("text", "")
    return ""

def extract_core_metadata(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extracts and generates core metadata from Crawler Metadata.

    Includes brand, category, status, price, and a synthesized name.

    Args:
        product (Dict[str, Any]): Raw crawler product JSON.

    Returns:
        Dict[str, Any]: A dictionary with core standardized fields.
    """
    product_id = product.get("code", "")

    # Safely extract brand
    brand = get_attribute(product.get("attributes", []), "brand")

    # Safely extract category
    categories = product.get("categories")
    if isinstance(categories, list) and categories:
        category = categories[0].get("text", "")
    else:
        category = ""

    # Safely extract price
    price = product.get("listPrice") or {}
    amount = price.get("amount")
    currency = price.get("currency", "USD")
    try:
        price_usd = f"{float(amount):.2f} {currency}"
    except (TypeError, ValueError):
        price_usd = ""

    # Determine status
    status = "discontinued" if product.get("isDiscontinued") else "active"

    # Synthesize name
    name_parts = [brand, category, product_id]
    name = " ".join(part for part in name_parts if part) or "Unnamed Product"

    return {
        "name": name,
        "brand": brand,
        "category": category,
        "price_usd": price_usd,
        "status": status
    }

def standardize_product_json(raw_json: Dict[str,Any],metadata: Dict[str,Any]) ->  Dict[str,Any]:
    """
    Cleans and standardizes a raw scraped product JSON by removing unused or redundant fields.

    Args:
        raw_json (Dict[str, Any]): Raw product dictionary scraped from source.
        metadata (Dict[str, Any]): Metadata returned by the Crawler.

    Returns:
        Dict[str, Any]: Cleaned and standardized product dictionary, ready for export or storage.
    """
    
    logger = get_logger("Schema Validator")
    
    clean_json = {
        **extract_core_metadata(metadata),
        **raw_json
    }

    # Clean known irrelevant or duplicated fields
    for key in ["img_src", "pdf_src", "drawings"]:
        clean_json.pop(key, None)
    
    if clean_json.get("performance"):
        if clean_json["performance"].get("performance_curves"):
            del clean_json["performance"]["performance_curves"]
        if clean_json["performance"].get("associated_urls"):
            del clean_json["performance"]["associated_urls"]
    
    if clean_json.get("parts"):
        clean_json["bom"] = deduplicate_bom(clean_json.pop("parts"))
    
    try:
        return remove_empty_fields(Product(**clean_json).model_dump())
    except Exception as e:
        logger.error("Data did not pass Standard Schema validation")
        logger.error(f"Validation details: {e}")
        return remove_empty_fields(clean_json)
    