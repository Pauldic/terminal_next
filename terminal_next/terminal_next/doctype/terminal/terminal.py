import frappe
from frappe.model.document import Document
from frappe.utils import cint

class Terminal(Document):
    def validate(self):
        self.terminal_code = (self.terminal_code or "").strip().upper()
        self.terminal_name = (self.terminal_name or "").strip()
        if not self.terminal_code:
            frappe.throw("Terminal Code is required.")
        if not self.terminal_name:
            frappe.throw("Terminal Name is required.")
        if self.company and not frappe.db.exists("Company", self.company):
            frappe.throw("The selected Company does not exist.")
