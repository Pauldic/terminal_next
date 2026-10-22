import frappe
from frappe.model.document import Document
from frappe.utils import cint

class YardBlock(Document):
    def validate(self):
        self.block_name = (self.block_name or "").strip()
        self.block_code = (self.block_code or "").strip().upper()
        if not self.block_name or not self.block_code:
            frappe.throw("Block Name and Block Code are required.")
        if cint(self.bays) < 1 or cint(self.rows) < 1 or cint(self.tiers) < 1:
            frappe.throw("Bays, rows, and tiers must each be at least 1.")
        area = frappe.db.get_value("Terminal Area", self.terminal_area, ["terminal", "status"], as_dict=True)
        if not area:
            frappe.throw("Select a valid Terminal Area.")
        if area.terminal != self.terminal:
            frappe.throw("Yard Block and Terminal Area must belong to the same Terminal.")
        if area.status != "Active":
            frappe.throw("Cannot create or edit a Yard Block in an inactive or blocked area.")
        duplicate = frappe.db.exists(
            "Yard Block",
            {"terminal": self.terminal, "block_code": self.block_code, "name": ["!=", self.name or ""]},
        )
        if duplicate:
            frappe.throw(f"Block Code {self.block_code} already exists in this terminal.")

    def on_trash(self):
        if frappe.db.exists("Yard Slot", {"yard_block": self.name}):
            frappe.throw("This Yard Block has Yard Slots. Deactivate it instead of deleting it.")
