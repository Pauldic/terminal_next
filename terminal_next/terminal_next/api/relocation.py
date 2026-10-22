
import frappe
from frappe.utils import now_datetime


ALLOWED_REASONS = {
    "Discharge",
    "Receipt",
    "Relocation",
    "Delivery",
    "Inspection",
    "Reefer Handling",
    "Correction",
    "Other",
}


@frappe.whitelist(methods=["POST"])
def relocate_container(
    container,
    to_slot,
    reason="Relocation",
    notes=None,
    reference_number=None,
):
    """Move a container between yard slots using a submitted Yard Transfer."""

    if not frappe.has_permission("Container", "read"):
        frappe.throw(
            "You do not have permission to view containers.",
            frappe.PermissionError,
        )

    if not frappe.has_permission("Yard Slot", "read"):
        frappe.throw(
            "You do not have permission to view yard slots.",
            frappe.PermissionError,
        )

    if not frappe.has_permission("Container Movement", "create"):
        frappe.throw(
            "You do not have permission to create container movements.",
            frappe.PermissionError,
        )

    if not frappe.has_permission("Container Movement", "submit"):
        frappe.throw(
            "You do not have permission to submit container movements.",
            frappe.PermissionError,
        )

    if not container or not to_slot:
        frappe.throw("Container and destination slot are required.")

    if reason not in ALLOWED_REASONS:
        frappe.throw("Select a valid movement reason.")

    container_doc = frappe.get_doc("Container", container)

    if not container_doc.current_yard_slot:
        frappe.throw(
            "This container has no recorded yard location and cannot be "
            "relocated. Resolve its location first."
        )

    if not container_doc.current_terminal:
        frappe.throw(
            "This container has no recorded terminal. Resolve its location first."
        )

    if container_doc.current_yard_slot == to_slot:
        frappe.throw(
            "The destination is already the container's current location."
        )

    if container_doc.operational_status != "In Yard":
        frappe.throw(
            "Only containers with operational status In Yard can be relocated."
        )

    movement = frappe.get_doc(
        {
            "doctype": "Container Movement",
            "container": container_doc.name,
            "movement_type": "Yard Transfer",
            "terminal": container_doc.current_terminal,
            "from_slot": container_doc.current_yard_slot,
            "to_slot": to_slot,
            "movement_time": now_datetime(),
            "reason": reason,
            "reference_number": reference_number,
            "operator": frappe.session.user,
            "notes": notes,
        }
    )

    movement.insert()
    movement.submit()

    return {
        "success": True,
        "message": "Container relocated successfully.",
        "container": container_doc.name,
        "container_number": container_doc.container_number,
        "movement": movement.name,
        "terminal": movement.terminal,
        "from_slot": movement.from_slot,
        "to_slot": movement.to_slot,
        "operational_status": "In Yard",
    }
