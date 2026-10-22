import frappe
from frappe.model.document import Document

class TerminalArea(Document):
    def validate(self):
        self.area_name = (self.area_name or "").strip()
        self.area_code = (self.area_code or "").strip().upper()
        if not self.area_name or not self.area_code:
            frappe.throw("Area Name and Area Code are required.")
        if not frappe.db.exists("Terminal", self.terminal):
            frappe.throw("Select a valid Terminal.")
        duplicate = frappe.db.exists(
            "Terminal Area",
            {"terminal": self.terminal, "area_code": self.area_code, "name": ["!=", self.name or ""]},
        )
        if duplicate:
            frappe.throw(f"Area Code {self.area_code} already exists in this terminal.")
