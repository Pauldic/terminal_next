
import frappe
from frappe.model.document import Document
from frappe.utils import cint


class YardSlot(Document):
    def autoname(self):
        """Generate the slot name before Frappe runs validate()."""
        if self.yard_block and self.bay and self.row and self.tier:
            self.slot_code = (f"{self.yard_block}-{cint(self.bay):02d}-{cint(self.row):02d}-{cint(self.tier):02d}")
            self.name = self.slot_code

    def validate(self):
        block = frappe.db.get_value(
            "Yard Block",
            self.yard_block,
            ["terminal", "terminal_area", "bays", "rows", "tiers", "status"],
            as_dict=True,
        )

        if not block:
            frappe.throw("Select a valid Yard Block.")

        if (self.terminal != block.terminal or self.terminal_area != block.terminal_area):
            frappe.throw("Terminal and Terminal Area must match the selected Yard Block.")

        if block.status != "Active":
            frappe.throw("Cannot create or edit slots in an inactive or blocked Yard Block.")

        if not (1 <= cint(self.bay) <= cint(block.bays)):
            frappe.throw(f"Bay must be between 1 and {block.bays}.")

        if not (1 <= cint(self.row) <= cint(block.rows)):
            frappe.throw(f"Row must be between 1 and {block.rows}.")

        if not (1 <= cint(self.tier) <= cint(block.tiers)):
            frappe.throw(f"Tier must be between 1 and {block.tiers}.")

        expected_code = (f"{self.yard_block}-{cint(self.bay):02d}-{cint(self.row):02d}-{cint(self.tier):02d}")

        # A slot's physical identity must not change after creation.
        if not self.is_new() and self.name != expected_code:
            frappe.throw("A Yard Slot's block, bay, row, and tier cannot be changed after creation. Create a new slot if the layout changes.")

        self.slot_code = expected_code

        duplicate = frappe.db.exists(
            "Yard Slot",
            {
                "yard_block": self.yard_block,
                "bay": self.bay,
                "row": self.row,
                "tier": self.tier,
                "name": ["!=", self.name or ""],
            },
        )

        if duplicate:
            frappe.throw(f"Yard Slot {expected_code} already exists.")

        if self.current_container and self.status != "Available":
            frappe.throw("An occupied slot cannot be blocked or placed under maintenance.")

    def on_trash(self):
        if self.current_container:
            frappe.throw("Cannot delete an occupied Yard Slot.")

        if (frappe.db.exists("Container Movement", {"from_slot": self.name, "docstatus": 1})
            or frappe.db.exists("Container Movement", {"to_slot": self.name, "docstatus": 1})):
            frappe.throw("This Yard Slot has submitted movement history and cannot be deleted.")
