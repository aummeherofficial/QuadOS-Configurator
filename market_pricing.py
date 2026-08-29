"""QuadOS market-style pricing and automatic bundle discounts.

The project keeps its product/configuration dictionaries in config.py.
This module displays the configured Indian market-oriented retail prices and
calculates the best eligible bundle offer. Prices are representative catalogue
prices, not a live retailer feed.
"""

from __future__ import annotations

from typing import Iterable, Mapping, Tuple

# Keep configured prices as the displayed/checkout prices.
MARKET_PRICE_FACTOR = 1.00

# Round displayed/checkout prices to normal retail increments.
ROUND_TO = 100


def market_price(price: float) -> float:
    """Convert a project list price into a rounded market-style selling price."""
    value = max(float(price or 0), 0.0) * MARKET_PRICE_FACTOR
    return float(round(value / ROUND_TO) * ROUND_TO)


def calculate_bundle_discount(cart: Iterable[Mapping]) -> Tuple[float, str]:
    """Return (discount_percent, offer_text) for the best eligible cart offer.

    Accessories may be purchased alone and receive no bundle discount.
    The highest single offer is used; discounts never stack.
    """
    items = list(cart or [])
    if not items:
        return 0.0, ""

    categories = {
        str(item.get("category", ""))
        for item in items
        if item.get("category")
    }

    accessory_items = [
        item for item in items
        if str(item.get("category", "")).startswith(
            ("accessory:", "mobile_accessory:")
        )
    ]
    non_accessory_categories = categories - {
        c for c in categories
        if c.startswith(("accessory:", "mobile_accessory:"))
    }

    accessory_count = len(accessory_items)
    device_type = str(
        getattr(__import__("streamlit"), "session_state", {}).get(
            "cart_device_type", ""
        )
    )

    # Complete Windows PC core: CPU + motherboard + RAM + storage + PSU + cabinet
    pc_core = {"cpu", "motherboard", "ram", "storage", "power_supply", "cabinet"}
    # Complete macOS core: processor + memory + storage + display
    mac_core = {"processor", "memory", "storage", "display"}
    # Complete iOS / Android core
    iphone_core = {
        "iphone_display", "iphone_battery", "iphone_ram",
        "iphone_storage", "iphone_processor", "iphone_connectivity"
    }
    android_core = {
        "android_display", "android_battery", "android_ram",
        "android_storage", "android_processor", "android_connectivity"
    }

    offers = []

    if device_type == "PC":
        os_name = str(
            getattr(__import__("streamlit"), "session_state", {}).get(
                "cart_operating_system", "Windows"
            )
        )
        if os_name == "Windows" and pc_core.issubset(non_accessory_categories):
            offers.append((10.0, "Complete Windows PC — 10% bundle discount"))
            if "gpu" in non_accessory_categories:
                offers.append((12.0, "Complete Windows PC + GPU — 12% bundle discount"))
            if "monitor" in non_accessory_categories:
                offers.append((12.0, "Complete PC + Monitor — 12% bundle discount"))
        elif os_name == "macOS" and mac_core.issubset(non_accessory_categories):
            offers.append((8.0, "Complete macOS setup — 8% bundle discount"))
            if "keyboard" in non_accessory_categories and "mouse" in non_accessory_categories:
                offers.append((10.0, "Complete Mac setup + peripherals — 10% bundle discount"))

        if non_accessory_categories and accessory_count >= 2:
            offers.append((10.0, "PC + 2 or more accessories — 10% bundle discount"))
        elif non_accessory_categories and accessory_count >= 1:
            offers.append((6.0, "PC + accessory — 6% bundle discount"))

    elif device_type == "Mobile":
        if iphone_core.issubset(non_accessory_categories) or android_core.issubset(non_accessory_categories):
            offers.append((7.0, "Complete smartphone — 7% bundle discount"))
            if accessory_count >= 2:
                offers.append((10.0, "Smartphone + 2 or more accessories — 10% bundle discount"))
            elif accessory_count >= 1:
                offers.append((8.0, "Smartphone + accessory — 8% bundle discount"))

    if not offers:
        return 0.0, ""

    return max(offers, key=lambda x: x[0])
