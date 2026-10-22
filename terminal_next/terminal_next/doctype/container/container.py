
import re

import frappe
from frappe.model.document import Document
from frappe.utils import flt


_CONTAINER_RE = re.compile(r"^[A-Z]{4}[0-9]{7}$")


class Container(Document):
    def validate(self):
        self.container_number = (
            (self.container_number or "").strip().upper().replace(" ", "")
        )

        if not _CONTAINER_RE.fullmatch(self.container_number):
            frappe.throw(
                "Container Number must contain 4 letters followed by 7 digits "
                "(ISO 6346 format)."
            )

        if flt(self.tare_weight_kg) < 0 or flt(self.gross_weight_kg) < 0:
            frappe.throw("Container weights cannot be negative.")

        if (
            self.gross_weight_kg
            and self.tare_weight_kg
            and self.gross_weight_kg < self.tare_weight_kg
        ):
            frappe.throw("Gross Weight cannot be less than Tare Weight.")

        if self.is_new():
            if self.current_yard_slot or self.current_terminal:
                frappe.throw(
                    "Set a container's current location through a submitted "
                    "Container Movement."
                )
        else:
            old = frappe.db.get_value(
                "Container",
                self.name,
                ["current_yard_slot", "current_terminal"],
                as_dict=True,
            )

            if old and (
                old.current_yard_slot != self.current_yard_slot
                or old.current_terminal != self.current_terminal
            ):
                frappe.throw(
                    "Current location is controlled by submitted Container Movements."
                )
