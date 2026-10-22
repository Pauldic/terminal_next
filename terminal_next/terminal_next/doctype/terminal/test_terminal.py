import frappe
from frappe.tests.utils import FrappeTestCase

class TestTerminal(FrappeTestCase):
    def test_terminal_code_is_normalized(self):
        terminal = frappe.get_doc({
            "doctype": "Terminal",
            "terminal_name": "Test Terminal",
            "terminal_code": " tst1 ",
            "status": "Active",
        }).insert()
        self.assertEqual(terminal.terminal_code, "TST1")
