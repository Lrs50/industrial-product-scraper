from typing import Dict, Any,List
from collections import defaultdict

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


def standardize_product_json(raw_json: Dict[str,Any]) ->  Dict[str,Any]:
    """
    Cleans and standardizes a raw scraped product JSON by removing unused or redundant fields.

    Args:
        raw_json (Dict[str, Any]): Raw product dictionary scraped from source.

    Returns:
        Dict[str, Any]: Cleaned and standardized product dictionary, ready for export or storage.
    """
    
    clean_json = remove_empty_fields(raw_json)
    
    if clean_json.get("img_src"):
        del clean_json["img_src"]
    
    if clean_json.get("pdf_src"):
        del clean_json["pdf_src"]
    
    if clean_json.get("drawings"):
        del clean_json["drawings"]
    
    if clean_json.get("performance"):
        if clean_json["performance"].get("performance_curves"):
            del clean_json["performance"]["performance_curves"]
        if clean_json["performance"].get("associated_urls"):
            del clean_json["performance"]["performance_curves"]
    
    if clean_json.get("parts"):
        clean_json["bom"] = deduplicate_bom(clean_json.pop("parts"))
    
    return clean_json