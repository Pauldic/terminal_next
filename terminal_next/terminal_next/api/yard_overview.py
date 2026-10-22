
import frappe


@frappe.whitelist(methods=["GET"])
def get_yard_overview(terminal, terminal_area=None, yard_block=None):
    """Return terminal areas, blocks, and slots for the Yard Overview UI."""

    if not terminal:
        frappe.throw("Select a terminal.")

    for doctype in ("Terminal", "Terminal Area", "Yard Block", "Yard Slot"):
        if not frappe.has_permission(doctype, "read"):
            frappe.throw(
                f"You do not have permission to view {doctype} records.",
                frappe.PermissionError,
            )

    terminal_doc = frappe.db.get_value(
        "Terminal",
        terminal,
        ["name", "terminal_name", "status"],
        as_dict=True,
    )

    if not terminal_doc:
        frappe.throw("The selected terminal does not exist.")

    if not terminal_doc.status:
        frappe.throw("The selected terminal is inactive.")

    area_filters = {"terminal": terminal}
    if terminal_area:
        area_filters["name"] = terminal_area

    areas = frappe.get_list(
        "Terminal Area",
        filters=area_filters,
        fields=["name", "area_name", "area_code", "area_type", "status"],
        order_by="area_name asc",
        page_length=0,
    )

    block_filters = {"terminal": terminal}
    if terminal_area:
        block_filters["terminal_area"] = terminal_area

    blocks = frappe.get_list(
        "Yard Block",
        filters=block_filters,
        fields=[
            "name",
            "block_name",
            "block_code",
            "terminal_area",
            "bays",
            "rows",
            "tiers",
            "status",
        ],
        order_by="block_code asc",
        page_length=0,
    )

    slots = []
    containers_by_name = {}

    # Return the physical grid only for a selected block.
    if yard_block:
        selected_block = next(
            (block for block in blocks if block.name == yard_block),
            None,
        )

        if not selected_block:
            frappe.throw(
                "The selected yard block does not belong to this terminal "
                "and selected area."
            )

        slots = frappe.get_list(
            "Yard Slot",
            filters={
                "terminal": terminal,
                "yard_block": yard_block,
            },
            fields=[
                "name",
                "slot_code",
                "terminal_area",
                "yard_block",
                "bay",
                "row",
                "tier",
                "status",
                "current_container",
            ],
            order_by="bay asc, row asc, tier asc",
            page_length=0,
        )

        container_names = list({
            slot.current_container
            for slot in slots
            if slot.current_container
        })

        if container_names and frappe.has_permission("Container", "read"):
            containers = frappe.get_list(
                "Container",
                filters={"name": ["in", container_names]},
                fields=["name", "container_number", "operational_status"],
                page_length=0,
            )
            containers_by_name = {
                container.name: container
                for container in containers
            }

        for slot in slots:
            container = containers_by_name.get(slot.current_container)
            slot["container_number"] = (
                container.container_number if container else None
            )
            slot["container_status"] = (
                container.operational_status if container else None
            )

    return {
        "terminal": terminal_doc,
        "areas": areas,
        "blocks": blocks,
        "selected_block": yard_block,
        "slots": slots,
    }

