#terminal_next/api/receiving.py
import frappe
from frappe.utils import now_datetime


RECEIVABLE_STATUSES = {"Expected", "Out-Gated"}


@frappe.whitelist(methods=["POST"])
def receive_container(
    container_number,
    terminal,
    to_slot,
    container_type="Dry",
    length_ft="20",
    iso_size_type=None,
    tare_weight_kg=None,
    gross_weight_kg=None,
    shipping_line=None,
    seal_number=None,
    notes=None,
    reason=None):
    """Register a new container if needed, then receive it into the yard."""

    container_number = (
        (container_number or "").strip().upper().replace(" ", "")
    )

    if not container_number:
        frappe.throw("Container Number is required.")

    if not terminal:
        frappe.throw("Select a Terminal.")

    if not to_slot:
        frappe.throw("Select a destination yard slot.")

    # The terminal must exist and be active.
    terminal_status = frappe.db.get_value(
        "Terminal", terminal, "status"
    )

    if terminal_status is None:
        frappe.throw("Select a valid Terminal.")

    if not int(terminal_status):
        frappe.throw("The selected Terminal is inactive.")

    # Confirm the destination belongs to the selected terminal.
    slot = frappe.db.get_value(
        "Yard Slot",
        to_slot,
        ["terminal", "status", "current_container"],
        as_dict=True,
    )

    if not slot:
        frappe.throw("Select a valid destination yard slot.")

    if slot.terminal != terminal:
        frappe.throw(
            "The destination slot must belong to the selected terminal."
        )

    if slot.status != "Available" or slot.current_container:
        frappe.throw("The destination slot is not available.")

    # Find an existing container before checking Container create permission.
    existing_name = frappe.db.get_value(
        "Container",
        {"container_number": container_number},
        "name",
    )

    created_container = False

    if existing_name:
        container = frappe.get_doc("Container", existing_name)

        # A recorded location must be changed through the movement workflow.
        if container.current_yard_slot or container.current_terminal:
            frappe.throw(
                "This container already has a recorded location. "
                "Use the appropriate movement workflow instead."
            )

        # Do not allow unrelated operational states to enter through Gate In.
        if container.operational_status not in RECEIVABLE_STATUSES:
            frappe.throw(
                f"Container {container.container_number} cannot be received "
                f"from its current status: "
                f"{container.operational_status or 'Not Set'}."
            )

    else:
        if not frappe.has_permission("Container", "create"):
            frappe.throw(
                "You do not have permission to register new containers.",
                frappe.PermissionError,
            )

        container = frappe.get_doc({
            "doctype": "Container",
            "container_number": container_number,
            "container_type": container_type,
            "length_ft": length_ft,
            "iso_size_type": iso_size_type,
            "tare_weight_kg": tare_weight_kg,
            "gross_weight_kg": gross_weight_kg,
            "shipping_line": shipping_line,
            "seal_number": seal_number,
            "notes": notes,
            "operational_status": "Expected",
        })

        container.insert()
        created_container = True

    if not frappe.has_permission("Container Movement", "create"):
        frappe.throw(
            "You do not have permission to create Container Movements.",
            frappe.PermissionError,
        )

    if not frappe.has_permission("Container Movement", "submit"):
        frappe.throw(
            "You do not have permission to submit Container Movements.",
            frappe.PermissionError,
        )

    movement = frappe.get_doc({
        "doctype": "Container Movement",
        "movement_type": "Gate In",
        "container": container.name,
        "terminal": terminal,
        "to_slot": to_slot,
        "movement_time": now_datetime(),
        "reason": reason or "Gate-in receiving",
    })

    movement.insert()
    movement.submit()

    return {
        "success": True,
        "created_container": created_container,
        "container": container.name,
        "container_number": container.container_number,
        "movement": movement.name,
        "terminal": terminal,
        "yard_slot": to_slot,
        "operational_status": "In Yard",
    }



@frappe.whitelist(methods=["GET"])
def get_receiving_terminals():
    """Return active terminals visible to the current user."""
    if not frappe.has_permission("Terminal", "read"):
        frappe.throw(
            "You do not have permission to view terminals.",
            frappe.PermissionError,
        )

    return frappe.get_list(
        "Terminal",
        filters={"status": 1},
        fields=["name", "terminal_name", "terminal_code"],
        order_by="terminal_name asc",
        page_length=0,
    )


@frappe.whitelist(methods=["GET"])
def lookup_container(container_number):
    """Look up a container and report whether Gate In is permitted."""
    container_number = ((container_number or "").strip().upper().replace(" ", ""))

    if not container_number:
        frappe.throw("Container Number is required.")

    if not frappe.has_permission("Container", "read"):
        frappe.throw(
            "You do not have permission to view containers.",
            frappe.PermissionError,
        )

    name = frappe.db.get_value(
        "Container",
        {"container_number": container_number},
        "name",
    )

    if not name:
        return {
            "exists": False,
            "can_receive": frappe.has_permission("Container", "create"),
            "reason": (
                None
                if frappe.has_permission("Container", "create")
                else "You do not have permission to register new containers."
            ),
            "container": None,
        }

    container = frappe.get_doc("Container", name)

    if container.current_yard_slot or container.current_terminal:
        can_receive = False
        reason = (
            "This container already has a recorded location. "
            "Use the appropriate movement workflow instead."
        )
    elif container.operational_status not in RECEIVABLE_STATUSES:
        can_receive = False
        reason = (
            f"This container cannot be received from its current status: "
            f"{container.operational_status or 'Not Set'}."
        )
    else:
        can_receive = True
        reason = None

    return {
        "exists": True,
        "can_receive": can_receive,
        "reason": reason,
        "container": {
            "name": container.name,
            "container_number": container.container_number,
            "container_type": container.container_type,
            "length_ft": container.length_ft,
            "iso_size_type": container.iso_size_type,
            "tare_weight_kg": container.tare_weight_kg,
            "gross_weight_kg": container.gross_weight_kg,
            "shipping_line": container.shipping_line,
            "seal_number": container.seal_number,
            "operational_status": container.operational_status,
            "current_terminal": container.current_terminal,
            "current_yard_slot": container.current_yard_slot,
        },
    }


@frappe.whitelist(methods=["GET"])
def get_available_yard_slots(terminal):
    """Return available, unoccupied yard slots in an active terminal."""
    if not frappe.has_permission("Terminal", "read"):
        frappe.throw(
            "You do not have permission to view terminals.",
            frappe.PermissionError,
        )

    if not frappe.has_permission("Yard Slot", "read"):
        frappe.throw(
            "You do not have permission to view yard slots.",
            frappe.PermissionError,
        )

    terminal_status = frappe.db.get_value(
        "Terminal", terminal, "status"
    )

    if terminal_status is None:
        frappe.throw("Select a valid Terminal.")

    if not int(terminal_status):
        frappe.throw("The selected Terminal is inactive.")

    slots = frappe.get_list(
        "Yard Slot",
        filters={
            "terminal": terminal,
            "status": "Available",
        },
        fields=[
            "name",
            "slot_code",
            "terminal_area",
            "yard_block",
            "bay",
            "row",
            "tier",
            "current_container",
        ],
        order_by="yard_block asc, bay asc, row asc, tier asc",
        page_length=0,
    )

    # Also exclude slots with an existing container assignment.
    return [
        {
            "name": slot.name,
            "slot_code": slot.slot_code,
            "terminal_area": slot.terminal_area,
            "yard_block": slot.yard_block,
            "bay": slot.bay,
            "row": slot.row,
            "tier": slot.tier,
        }
        for slot in slots
        if not slot.current_container
    ]



@frappe.whitelist(methods=["GET"])
def get_container_inventory(
    search=None,
    terminal=None,
    operational_status=None,
    container_type=None,
    start=0,
    page_length=50):
    """Return a paginated, permission-aware container inventory."""
    if not frappe.has_permission("Container", "read"):
        frappe.throw(
            "You do not have permission to view container inventory.",
            frappe.PermissionError,
        )

    start = max(int(start or 0), 0)
    page_length = min(max(int(page_length or 50), 1), 100)

    filters = {}

    if terminal:
        filters["current_terminal"] = terminal

    if operational_status:
        filters["operational_status"] = operational_status

    if container_type:
        filters["container_type"] = container_type

    or_filters = None
    search = (search or "").strip()

    if search:
        search_like = f"%{frappe.db.escape(search, percent=False)}%"
        or_filters = [
            ["Container", "container_number", "like", search_like],
            ["Container", "name", "like", search_like],
        ]

    # Fetch one extra row to determine whether another page exists.
    rows = frappe.get_list(
        "Container",
        filters=filters,
        or_filters=or_filters,
        fields=[
            "name",
            "container_number",
            "container_type",
            "length_ft",
            "iso_size_type",
            "shipping_line",
            "operational_status",
            "current_terminal",
            "current_yard_slot",
            "modified",
        ],
        order_by="modified desc",
        start=start,
        page_length=page_length + 1,
    )

    has_more = len(rows) > page_length
    rows = rows[:page_length]

    return {
        "data": rows,
        "start": start,
        "page_length": page_length,
        "has_more": has_more,
    }


