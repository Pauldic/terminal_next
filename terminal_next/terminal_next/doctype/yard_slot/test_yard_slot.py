import frappe
from frappe.tests.utils import FrappeTestCase

class TestYardSlot(FrappeTestCase):
    def setUp(self):
        self.terminal = frappe.get_doc({
            "doctype": "Terminal", "terminal_name": "Test Terminal",
            "terminal_code": "TSTYARD", "status": "Active",
        }).insert(ignore_if_duplicate=True)
        self.area = frappe.get_doc({
            "doctype": "Terminal Area", "terminal": self.terminal.name,
            "area_name": "Container Yard", "area_code": "CY",
            "area_type": "Container Yard", "status": "Active",
        }).insert(ignore_if_duplicate=True)
        self.block = frappe.get_doc({
            "doctype": "Yard Block", "terminal": self.terminal.name,
            "terminal_area": self.area.name, "block_name": "Block A",
            "block_code": "A", "bays": 3, "rows": 2, "tiers": 4, "status": "Active",
        }).insert(ignore_if_duplicate=True)

    def test_slot_code_and_bounds(self):
        slot = frappe.get_doc({
            "doctype": "Yard Slot", "terminal": self.terminal.name,
            "terminal_area": self.area.name, "yard_block": self.block.name,
            "bay": 1, "row": 2, "tier": 3, "status": "Available",
        }).insert()
        self.assertEqual(slot.slot_code, f"{self.block.name}-01-02-03")

    def test_reject_slot_outside_block_dimensions(self):
        with self.assertRaises(frappe.ValidationError):
            frappe.get_doc({
                "doctype": "Yard Slot", "terminal": self.terminal.name,
                "terminal_area": self.area.name, "yard_block": self.block.name,
                "bay": 4, "row": 1, "tier": 1, "status": "Available",
            }).insert()
    
    def test_slot_name_is_generated_before_insert(self):
        slot = frappe.get_doc({
            "doctype": "Yard Slot",
            "terminal": self.terminal.name,
            "terminal_area": self.area.name,
            "yard_block": self.block.name,
            "bay": 1,
            "row": 1,
            "tier": 1,
            "status": "Available",
        })

        expected_code = f"{self.block.name}-01-01-01"

        slot.insert()

        self.assertEqual(slot.name, expected_code)
        self.assertEqual(slot.slot_code, expected_code)
        self.assertTrue(frappe.db.exists("Yard Slot", expected_code))
