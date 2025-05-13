# Industrial Product Scraper

A scraper for industrial products that collects detailed product information and organizes it into a structured JSON format.

## Description

This project automates the collection of industrial product data from the [baldor.com](https://www.baldor.com/) website. It extracts information such as product identifiers, prices, technical specifications, components, accessories, and images, storing them in a standardized JSON structure to facilitate analysis and integration with other systems.

## Requirements

- Python 3.8+
- UV (Python package manager)

## Installation

1. Clone the repository:

   ```bash
   git clone https://github.com/your-username/industrial-product-scraper.git
   cd industrial-product-scraper
   ```
2. Make sure you have UV installed. If not, install it by following the instructions at [https://github.com/astral-sh/uv](https://github.com/astral-sh/uv).

## Execution

To run the scraper, use the command:

```bash
uv run src/main.py
```

This command will start the scraping process and the results will be stored in the `output/` directory in JSON format.

## Output JSON Format

The data collected from baldor.com is structured according to the schema below:

### Product Structure

| Field           | Type   | Description                                                                                                                 | Required |
| --------------- | ------ | --------------------------------------------------------------------------------------------------------------------------- | -------- |
| `product_id`  | string | Unique product identifier                                                                                                   | Yes      |
| `name`        | string | Product name                                                                                                                | No       |
| `description` | string | Detailed product description                                                                                                | No       |
| `brand`       | string | Product brand                                                                                                               | No       |
| `category`    | string | Product category                                                                                                            | No       |
| `status`      | string | Product status ("active" or "discontinued")                                                                                 | Yes      |
| `price_usd`   | string | Product price in US dollars                                                                                                 | No       |
| `info`        | object | Additional product information as key-value pairs                                                                           | No       |
| `specs`       | object | Technical specifications as key-value pairs                                                                                 | No       |
| `bom`         | array  | List of components (Bill of Materials)                                                                                      | No       |
| `accessories` | array  | List of compatible accessories                                                                                              | No       |
| `nameplate`   | object | Product nameplate information                                                                                               | No       |
| `assets`      | object | Downloaded resources, including images, manuals, and other related files, organized and stored within the assets directory. | No       |
