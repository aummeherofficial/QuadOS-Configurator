"""QuadOS market-style pricing and automatic bundle discounts.

The project keeps its product/configuration dictionaries in config.py.
This module is the single source of truth for displayed market-style prices
and automatic bundle discounts. Prices are representative catalogue prices,
not a live retailer feed.
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
    """Return the best single bundle discount for the current cart.

    This is the only bundle-discount calculation used by QuadOS.
    Discounts never stack. Accessories alone do not qualify because the
    order-validation layer requires at least one device component.
    """
    items = list(cart or [])
    if not items:
        return 0.0, ""

    def category(item):
        return str(item.get("category", "")).strip().lower()

    accessories = [
        item for item in items
        if category(item).startswith(("accessory:", "mobile_accessory:"))
        or str(item.get("name", "")).strip().lower().startswith("accessory - ")
    ]
    core_items = [item for item in items if item not in accessories]

    core_categories = {
        category(item)
        for item in core_items
        if category(item)
    }
    core_count = len(core_items)
    accessory_count = len(accessories)

    # The app records these values when an item is added to the cart.
    # Keeping the fallback defaults here makes the function safe for an
    # older session state as well.
    try:
        import streamlit as st
        device_type = str(st.session_state.get("cart_device_type", "")).strip()
        operating_system = str(st.session_state.get("cart_operating_system", "")).strip()
    except Exception:
        device_type = ""
        operating_system = ""

    if not device_type:
        if any(
            c.startswith(("iphone_", "android_", "mobile_accessory:"))
            for c in core_categories | {category(item) for item in accessories}
        ):
            device_type = "Mobile"
        else:
            device_type = "PC"

    offers = []

    if core_count == 0:
        # Accessories alone do not qualify for a bundle discount.
        return 0.0, ""

    elif device_type == "Mobile":
        iphone_core = {
            "iphone_display", "iphone_battery", "iphone_ram",
            "iphone_storage", "iphone_processor", "iphone_connectivity"
        }
        android_core = {
            "android_display", "android_battery", "android_ram",
            "android_storage", "android_processor", "android_connectivity"
        }

        if iphone_core.issubset(core_categories) or android_core.issubset(core_categories):
            offers.append((7.0, "Complete smartphone — 7% bundle discount"))
            if accessory_count >= 2:
                offers.append((10.0, "Smartphone + 2 accessories — 10% bundle discount"))
            elif accessory_count >= 1:
                offers.append((8.0, "Complete smartphone + accessory — 8% bundle discount"))
        elif core_count >= 4:
            offers.append((6.0, "4+ smartphone components — 6% discount"))
        elif core_count >= 3:
            offers.append((5.0, "3+ smartphone components — 5% discount"))
        elif core_count >= 2:
            offers.append((3.0, "Smartphone component combo — 3% discount"))

    elif operating_system == "macOS":
        mac_core = {"processor", "memory", "storage", "display"}

        if mac_core.issubset(core_categories):
            offers.append((8.0, "Complete macOS setup — 8% bundle discount"))
            if "keyboard" in core_categories and "mouse" in core_categories:
                offers.append((10.0, "Complete Mac setup + peripherals — 10% bundle discount"))
            elif accessory_count >= 1:
                offers.append((10.0, "Complete Mac + accessory — 10% bundle discount"))
        elif core_count >= 4:
            offers.append((7.0, "4+ Mac components — 7% discount"))
        elif core_count >= 3:
            offers.append((5.0, "3+ Mac components — 5% discount"))
        elif core_count >= 2:
            offers.append((3.0, "Mac component combo — 3% discount"))

    else:
        pc_core = {
            "cpu", "motherboard", "ram", "storage", "power_supply", "cabinet"
        }

        if pc_core.issubset(core_categories):
            offers.append((10.0, "Complete Windows PC — 10% bundle discount"))
            if "gpu" in core_categories or "monitor" in core_categories:
                offers.append((12.0, "Complete PC + GPU/Monitor — 12% bundle discount"))
            if accessory_count >= 1:
                offers.append((12.0, "Complete PC + accessory — 12% bundle discount"))
        elif core_count >= 4:
            offers.append((7.0, "4+ PC components — 7% discount"))
        elif core_count >= 3:
            offers.append((5.0, "3+ PC components — 5% discount"))
        elif core_count >= 2:
            offers.append((3.0, "PC component combo — 3% discount"))

        # A non-complete PC plus accessories gets the standard accessory offer.
        if core_count >= 1:
            if accessory_count >= 2:
                offers.append((8.0, "PC + 2 accessories — 8% bundle discount"))
            elif accessory_count >= 1:
                offers.append((6.0, "PC + accessory — 6% bundle discount"))

    if not offers:
        return 0.0, ""

    # Only the highest eligible offer is applied.
    return max(offers, key=lambda offer: offer[0])
