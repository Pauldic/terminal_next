import frappe
from frappe.utils import now_datetime, add_days

def create_demo_data():
    frappe.clear_cache()
    print("🚀 Starting Terminal Next Demo Data Generation...")

    # 1. Get or Create a Company
    company = frappe.db.get_value("Company", {"is_group": 0}, "name")
    if not company:
        company = frappe.get_doc({
            "doctype": "Company",
            "company_name": "Demo Terminal Operations Ltd",
            "abbr": "DTOL",
            "default_currency": "USD",
            "country": "Nigeria"
        }).insert().name
        frappe.db.commit()

    # 2. Get or Create a Customer
    shipping_line_cust = frappe.db.get_value("Customer", {"customer_name": ["like", "%Demo Shipping%"]}, "name")
    if not shipping_line_cust:
        shipping_line_cust = frappe.get_doc({
            "doctype": "Customer",
            "customer_name": "Demo Global Shipping Line",
            "customer_group": "Commercial",
            "territory": "All Territories"
        }).insert().name
        frappe.db.commit()

    # 3. Create Terminal
    terminal_code = "LDWT"
    if not frappe.db.exists("Terminal", terminal_code):
        terminal = frappe.get_doc({
            "doctype": "Terminal",
            "terminal_name": "Lagos Deep Water Terminal",
            "terminal_code": terminal_code,
            "company": company,
            "status": 1,
            "address": "Lekki Free Trade Zone, Lagos, Nigeria",
            "timezone": "Africa/Lagos",
            "description": "Primary deep-water container terminal for demo operations."
        }).insert()
        frappe.db.commit()
        print(f"✅ Created Terminal: {terminal.terminal_name}")
    else:
        terminal = frappe.get_doc("Terminal", terminal_code)

    # 4. Create Terminal Area
    area_code = "IY"
    if not frappe.db.exists("Terminal Area", {"area_code": area_code, "terminal": terminal.name}):
        area = frappe.get_doc({
            "doctype": "Terminal Area",
            "naming_series": "TA.YY.-.######",
            "terminal": terminal.name,
            "area_name": "Import Yard",
            "area_code": area_code,
            "area_type": "Container Yard",
            "status": "Active",
            "description": "Main yard for imported full containers."
        }).insert()
        frappe.db.commit()
        print(f"✅ Created Terminal Area: {area.area_name}")
    else:
        area = frappe.get_doc("Terminal Area", {"area_code": area_code, "terminal": terminal.name})

    # 5. Create Yard Block
    block_code = "BLK-A"
    if not frappe.db.exists("Yard Block", {"block_code": block_code, "terminal": terminal.name}):
        block = frappe.get_doc({
            "doctype": "Yard Block",
            "naming_series": "YB.YY.-.######",
            "terminal": terminal.name,
            "terminal_area": area.name,
            "block_name": "Block A",
            "block_code": block_code,
            "bays": 5,
            "rows": 4,
            "tiers": 3,
            "status": "Active",
            "notes": "Standard dry and reefer block."
        }).insert()
        frappe.db.commit()
        print(f"✅ Created Yard Block: {block.block_name}")
    else:
        block = frappe.get_doc("Yard Block", {"block_code": block_code, "terminal": terminal.name})

    
    created_slots = []

    # 6. Create or reuse Yard Slots without clearing existing occupancy.
    for s in slots_to_create:
        actual_slot_code = (
            f"{block.name}-{s['bay']:02d}-{s['row']:02d}-{s['tier']:02d}"
        )

        existing_slot_name = frappe.db.get_value(
            "Yard Slot", {"slot_code": actual_slot_code}, "name"
        )

        if existing_slot_name:
            slot = frappe.get_doc("Yard Slot", existing_slot_name)

            # Never silently repurpose an existing slot.
            if (
                slot.terminal != terminal.name
                or slot.terminal_area != area.name
                or slot.yard_block != block.name
            ):
                frappe.throw(
                    f"Slot {actual_slot_code} belongs to a different yard location."
                )

            created_slots.append({"code": actual_slot_code, "name": slot.name})
            print(f"Reusing existing Slot: {actual_slot_code}")
        else:
            slot = frappe.new_doc("Yard Slot")
            slot.terminal = terminal.name
            slot.terminal_area = area.name
            slot.yard_block = block.name
            slot.bay = s["bay"]
            slot.row = s["row"]
            slot.tier = s["tier"]
            slot.slot_code = actual_slot_code
            slot.status = "Available"
            slot.insert()
            frappe.db.commit()

            created_slots.append({"code": actual_slot_code, "name": slot.name})
            print(f"Created new Slot: {actual_slot_code}")

    # 7. Create or reuse Containers and always resolve their intended slots.
    containers_data = [
        {
            "num": "MSKU1234567", "iso": "45G1", "type": "Dry", "len": "40",
            "tare": 3800, "gross": 30400, "status": "In Yard",
            "slot_idx": 0, "seal": "SL-9988",
        },
        {
            "num": "HLCU9876543", "iso": "22G1", "type": "Reefer", "len": "20",
            "tare": 2200, "gross": 25000, "status": "In Yard",
            "slot_idx": 1, "seal": "SL-7766",
        },
        {
            "num": "CMAU1122334", "iso": "45R1", "type": "Reefer", "len": "40",
            "tare": 4000, "gross": 32000, "status": "Expected",
            "slot_idx": None, "seal": "SL-5544",
        },
        {
            "num": "OOLU5566778", "iso": "22T1", "type": "Tank", "len": "20",
            "tare": 2500, "gross": 28000, "status": "In Yard",
            "slot_idx": 2, "seal": "SL-3322",
        },
    ]

    container_targets = {}

    for c in containers_data:
        target_slot = None

        if c["slot_idx"] is not None:
            target_slot = created_slots[c["slot_idx"]]["name"]

        container_name = frappe.db.get_value(
            "Container", {"container_number": c["num"]}, "name"
        )

        if not container_name:
            cont = frappe.new_doc("Container")
            cont.container_number = c["num"]
            cont.iso_size_type = c["iso"]
            cont.container_type = c["type"]
            cont.length_ft = c["len"]
            cont.tare_weight_kg = c["tare"]
            cont.gross_weight_kg = c["gross"]
            cont.shipping_line = shipping_line_cust
            cont.operational_status = (
                "Expected" if c["status"] == "Expected" else "Out-Gated"
            )
            cont.seal_number = c["seal"]
            cont.notes = "Demo container generated by script."
            cont.insert()
            frappe.db.commit()
            container_name = cont.name
            print(f"Created Container: {container_name}")
        else:
            print(f"Reusing Container: {container_name}")

        container_targets[container_name] = {
            "number": c["num"],
            "target_slot": target_slot,
            "desired_status": c["status"],
        }

    # 8. Reconcile demo Gate In movements through the existing controller.
    movements_created = 0

    for container_name, target in container_targets.items():
        target_slot = target["target_slot"]

        if not target_slot:
            continue

        container = frappe.get_doc("Container", container_name)

        # Already at the intended location: no new movement is needed.
        if (
            container.current_terminal == terminal.name
            and container.current_yard_slot == target_slot
            and container.operational_status == "In Yard"
        ):
            print(
                f"Already correctly located: {container.name} -> {target_slot}"
            )
            continue

        # Never silently move a container that has a different recorded location.
        if container.current_yard_slot or container.current_terminal:
            frappe.throw(
                f"Container {container.name} already has a recorded location "
                f"({container.current_terminal}, {container.current_yard_slot}). "
                "Resolve it through a valid Container Movement before rerunning."
            )

        # If a previous submitted Gate In exists but the location is missing,
        # do not create a duplicate or rewrite history.
        existing_gate_in = frappe.db.exists(
            "Container Movement",
            {
                "container": container.name,
                "movement_type": "Gate In",
                "docstatus": 1,
            },
        )
        if existing_gate_in:
            frappe.throw(
                f"Container {container.name} has submitted Gate In movement "
                f"{existing_gate_in} but no matching recorded location. "
                "Investigate this inconsistency before continuing."
            )

        slot = frappe.get_doc("Yard Slot", target_slot)

        if slot.current_container:
            frappe.throw(
                f"Target slot {target_slot} is already occupied by "
                f"{slot.current_container}."
            )

        if slot.status != "Available":
            frappe.throw(
                f"Target slot {target_slot} is {slot.status}, not Available."
            )

        movement = frappe.get_doc(
            {
                "doctype": "Container Movement",
                "naming_series": "CM.YY.-.######",
                "container": container.name,
                "movement_type": "Gate In",
                "terminal": terminal.name,
                "to_slot": target_slot,
                "movement_time": add_days(now_datetime(), -2),
                "reason": "Discharge",
                "reference_number": f"BL-{target['number'][-4:]}",
                "operator": "Administrator",
                "notes": "Initial gate-in for demo data.",
            }
        )

        # Explicit guard gives a clear error before the controller runs.
        if not movement.to_slot:
            frappe.throw(
                f"Destination slot is empty for {container.name}."
            )

        movement.insert()
        movement.submit()
        frappe.db.commit()

        movements_created += 1
        print(
            f"Submitted Gate In: {container.name} -> {target_slot}"
        )

    print(f"Created and submitted {movements_created} Container Movements")
    print("Demo data generation completed successfully!")


if __name__ == "__main__":
    create_demo_data()