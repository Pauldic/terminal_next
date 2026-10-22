import frappe
from frappe.tests.utils import FrappeTestCase

class TestContainerMovement(FrappeTestCase):
    def setUp(self):
        suffix = frappe.generate_hash(length=5).upper()
        self.terminal = frappe.get_doc({
            "doctype": "Terminal", "terminal_name": "Test Terminal " + suffix,
            "terminal_code": "TM" + suffix, "status": "Active",
        }).insert()
        self.area = frappe.get_doc({
            "doctype": "Terminal Area", "terminal": self.terminal.name,
            "area_name": "Yard " + suffix, "area_code": "Y" + suffix,
            "area_type": "Container Yard", "status": "Active",
        }).insert()
        self.block = frappe.get_doc({
            "doctype": "Yard Block", "terminal": self.terminal.name,
            "terminal_area": self.area.name, "block_name": "Block A",
            "block_code": "A" + suffix, "bays": 2, "rows": 2, "tiers": 3,
            "status": "Active",
        }).insert()
        self.slot1 = self.make_slot(1, 1, 1)
        self.slot2 = self.make_slot(2, 1, 1)
        self.container = frappe.get_doc({
            "doctype": "Container", "container_number": "MSCU" + str(int(frappe.generate_hash(length=8), 16) % 10000000).zfill(7),
            "container_type": "Dry", "length_ft": "20",
        }).insert()

    def make_slot(self, bay, row, tier):
        return frappe.get_doc({
            "doctype": "Yard Slot", "terminal": self.terminal.name,
            "terminal_area": self.area.name, "yard_block": self.block.name,
            "bay": bay, "row": row, "tier": tier, "status": "Available",
        }).insert()

    def test_gate_in_then_yard_transfer(self):
        gate_in = frappe.get_doc({
            "doctype": "Container Movement", "container": self.container.name,
            "movement_type": "Gate In", "terminal": self.terminal.name,
            "to_slot": self.slot1.name, "reason": "Receipt",
            "movement_time": frappe.utils.now_datetime(),
        }).insert()
        gate_in.submit()
        self.assertEqual(frappe.db.get_value("Container", self.container.name, "current_yard_slot"), self.slot1.name)
        self.assertEqual(frappe.db.get_value("Yard Slot", self.slot1.name, "current_container"), self.container.name)

        move = frappe.get_doc({
            "doctype": "Container Movement", "container": self.container.name,
            "movement_type": "Yard Transfer", "terminal": self.terminal.name,
            "from_slot": self.slot1.name, "to_slot": self.slot2.name,
            "reason": "Relocation", "movement_time": frappe.utils.now_datetime(),
        }).insert()
        move.submit()
        self.assertEqual(frappe.db.get_value("Container", self.container.name, "current_yard_slot"), self.slot2.name)
        self.assertFalse(frappe.db.get_value("Yard Slot", self.slot1.name, "current_container"))
        self.assertEqual(frappe.db.get_value("Yard Slot", self.slot2.name, "current_container"), self.container.name)

    def test_cannot_gate_in_container_twice(self):
        doc = frappe.get_doc({
            "doctype": "Container Movement", "container": self.container.name,
            "movement_type": "Gate In", "terminal": self.terminal.name,
            "to_slot": self.slot1.name, "reason": "Receipt",
            "movement_time": frappe.utils.now_datetime(),
        }).insert()
        doc.submit()
        second = frappe.get_doc({
            "doctype": "Container Movement", "container": self.container.name,
            "movement_type": "Gate In", "terminal": self.terminal.name,
            "to_slot": self.slot2.name, "reason": "Receipt",
            "movement_time": frappe.utils.now_datetime(),
        })
        with self.assertRaises(frappe.ValidationError):
            second.insert()
