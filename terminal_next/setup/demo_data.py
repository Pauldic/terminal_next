
import frappe
from frappe.utils import add_days, now_datetime


TERMINAL_CODE = "LDWT"
AREA_CODE = "IY"
BLOCK_CODE = "BLK-A"

CONTAINERS = [
    {
        "num": "MSKU1234567",
        "iso": "45G1",
        "type": "Dry",
        "length": 40,
        "tare": 3800,
        "gross": 30400,
        "status": "In Yard",
        "slot_idx": 0,
        "seal": "SL-9988",
    },
    {
        "num": "HLCU9876543",
        "iso": "22G1",
        "type": "Reefer",
        "length": 20,
        "tare": 2200,
        "gross": 25000,
        "status": "In Yard",
        "slot_idx": 1,
        "seal": "SL-7766",
    },
    {
        "num": "CMAU1122334",
        "iso": "45R1",
        "type": "Reefer",
        "length": 40,
        "tare": 4000,
        "gross": 32000,
        "status": "Expected",
        "slot_idx": None,
        "seal": "SL-5544",
    },
    {
        "num": "OOLU5566778",
        "iso": "22T1",
        "type": "Tank",
        "length": 20,
        "tare": 2500,
        "gross": 28000,
        "status": "In Yard",
        "slot_idx": 2,
        "seal": "SL-3322",
    },
]

SLOT_COORDINATES = [
    {"bay": 1, "row": 1, "tier": 1},
    {"bay": 1, "row": 1, "tier": 2},
    {"bay": 2, "row": 1, "tier": 1},
    {"bay": 3, "row": 2, "tier": 1},
]


def get_or_create_company():
    company = frappe.db.get_value(
        "Company", {"is_group": 0}, "name"
    )
    if company:
        return company

    doc = frappe.get_doc({
        "doctype": "Company",
        "company_name": "Demo Terminal Operations Ltd",
        "abbr": "DTOL",
        "default_currency": "USD",
        "country": "Nigeria",
    })
    doc.insert()
    print(f"Created Company: {doc.name}")
    return doc.name


def get_or_create_shipping_line():
    customer = frappe.db.get_value(
        "Customer",
        {"customer_name": ["like", "%Demo Shipping%"]},
        "name",
    )
    if customer:
        return customer

    doc = frappe.get_doc({
        "doctype": "Customer",
        "customer_name": "Demo Global Shipping Line",
        "customer_group": "Commercial",
        "territory": "All Territories",
    })
    doc.insert()
    print(f"Created Shipping Line Customer: {doc.name}")
    return doc.name


def get_or_create_terminal(company):
    name = frappe.db.get_value(
        "Terminal", {"terminal_code": TERMINAL_CODE}, "name"
    )
    if name:
        terminal = frappe.get_doc("Terminal", name)
        if not terminal.status:
            frappe.throw(
                f"Demo terminal {name} is inactive. Activate it first."
            )
        return terminal

    terminal = frappe.get_doc({
        "doctype": "Terminal",
        "terminal_name": "Lagos Deep Water Terminal",
        "terminal_code": TERMINAL_CODE,
        "company": company,
        "status": 1,
        "address": "Lekki Free Trade Zone, Lagos, Nigeria",
        "timezone": "Africa/Lagos",
        "description": (
            "Primary deep-water container terminal for demo operations."
        ),
    })
    terminal.insert()
    print(f"Created Terminal: {terminal.name}")
    return terminal


def get_or_create_area(terminal):
    name = frappe.db.get_value(
        "Terminal Area",
        {"area_code": AREA_CODE, "terminal": terminal.name},
        "name",
    )
    if name:
        return frappe.get_doc("Terminal Area", name)

    area = frappe.get_doc({
        "doctype": "Terminal Area",
        "naming_series": "TA.YY.-.######",
        "terminal": terminal.name,
        "area_name": "Import Yard",
        "area_code": AREA_CODE,
        "area_type": "Container Yard",
        "status": "Active",
        "description": "Main yard for imported full containers.",
    })
    area.insert()
    print(f"Created Terminal Area: {area.name}")
    return area


def get_or_create_block(terminal, area):
    name = frappe.db.get_value(
        "Yard Block",
        {"block_code": BLOCK_CODE, "terminal": terminal.name},
        "name",
    )
    if name:
        block = frappe.get_doc("Yard Block", name)
        if block.terminal_area != area.name:
            frappe.throw(
                f"Existing block {name} belongs to another terminal area."
            )
        if block.status != "Active":
            frappe.throw(f"Demo yard block {name} is not Active.")
        return block

    block = frappe.get_doc({
        "doctype": "Yard Block",
        "naming_series": "YB.YY.-.######",
        "terminal": terminal.name,
        "terminal_area": area.name,
        "block_name": "Block A",
        "block_code": BLOCK_CODE,
        "bays": 5,
        "rows": 4,
        "tiers": 3,
        "status": "Active",
        "notes": "Standard dry and reefer block.",
    })
    block.insert()
    print(f"Created Yard Block: {block.name}")
    return block


def get_or_create_slots(terminal, area, block):
    slots = []

    for coordinates in SLOT_COORDINATES:
        bay = coordinates["bay"]
        row = coordinates["row"]
        tier = coordinates["tier"]

        expected_code = (
            f"{block.name}-{bay:02d}-{row:02d}-{tier:02d}"
        )

        slot_name = frappe.db.get_value(
            "Yard Slot", {"slot_code": expected_code}, "name"
        )

        if slot_name:
            slot = frappe.get_doc("Yard Slot", slot_name)

            # Never rewrite an existing slot's physical identity.
            expected_identity = (
                terminal.name,
                area.name,
                block.name,
                bay,
                row,
                tier,
            )
            actual_identity = (
                slot.terminal,
                slot.terminal_area,
                slot.yard_block,
                slot.bay,
                slot.row,
                slot.tier,
            )
            if actual_identity != expected_identity:
                frappe.throw(
                    f"Slot {slot_name} has a conflicting physical identity. "
                    "Resolve it before generating demo data."
                )
        else:
            slot = frappe.get_doc({
                "doctype": "Yard Slot",
                "terminal": terminal.name,
                "terminal_area": area.name,
                "yard_block": block.name,
                "bay": bay,
                "row": row,
                "tier": tier,
                "status": "Available",
            })
            slot.insert()
            print(f"Created Yard Slot: {slot.name}")

        slots.append(slot)

    return slots


def get_container_by_number(container_number):
    name = frappe.db.get_value(
        "Container",
        {"container_number": container_number},
        "name",
    )
    return frappe.get_doc("Container", name) if name else None


def get_or_create_containers(shipping_line, slots, terminal):
    containers = {}

    # Validate existing records before modifying any container.
    for data in CONTAINERS:
        container = get_container_by_number(data["num"])

        if not container:
            continue

        target_slot = (
            slots[data["slot_idx"]]
            if data["slot_idx"] is not None
            else None
        )

        if container.current_terminal or container.current_yard_slot:
            already_correct = (
                data["status"] == "In Yard"
                and target_slot is not None
                and container.current_terminal == terminal.name
                and container.current_yard_slot == target_slot.name
                and container.operational_status == "In Yard"
                and target_slot.current_container == container.name
            )
            if not already_correct:
                frappe.throw(
                    f"Existing container {data['num']} has a recorded "
                    "location that conflicts with this demo layout. "
                    "No location fields will be overwritten."
                )

        elif frappe.db.exists(
            "Container Movement",
            {"container": container.name},
        ):
            frappe.throw(
                f"Container {data['num']} has movement history but no "
                "recorded location. Resolve that inconsistency before "
                "generating demo data."
            )

        containers[data["num"]] = container

    for data in CONTAINERS:
        container = containers.get(data["num"])

        if container:
            # Repair only a locationless record with no movement history.
            # The movement controller will establish its yard location.
            if (
                data["status"] == "In Yard"
                and container.operational_status != "Expected"
            ):
                container.operational_status = "Expected"
                container.save()
            elif (
                data["status"] == "Expected"
                and container.operational_status != "Expected"
            ):
                container.operational_status = "Expected"
                container.save()

            continue

        container = frappe.get_doc({
            "doctype": "Container",
            "container_number": data["num"],
            "iso_size_type": data["iso"],
            "container_type": data["type"],
            "length_ft": data["length"],
            "tare_weight_kg": data["tare"],
            "gross_weight_kg": data["gross"],
            "shipping_line": shipping_line,
            # A Gate In movement changes this to In Yard.
            "operational_status": "Expected",
            "seal_number": data["seal"],
            "notes": "Demo container generated by script.",
        })
        container.insert()
        containers[data["num"]] = container
        print(f"Created Container: {container.name}")

    return containers


def create_gate_in_if_needed(data, container, target_slot, terminal):
    # Idempotent: a correctly completed placement needs no new movement.
    if (
        container.operational_status == "In Yard"
        and container.current_terminal == terminal.name
        and container.current_yard_slot == target_slot.name
        and target_slot.current_container == container.name
    ):
        print(f"Already placed: {container.name} -> {target_slot.name}")
        return None

    if container.current_terminal or container.current_yard_slot:
        frappe.throw(
            f"Container {container.name} already has a location. "
            "Refusing to create another Gate In."
        )

    existing_movements = frappe.get_all(
        "Container Movement",
        filters={"container": container.name},
        fields=["name", "docstatus"],
        limit=1,
    )
    if existing_movements:
        frappe.throw(
            f"Container {container.name} has existing movement "
            f"{existing_movements[0].name}. Refusing to duplicate history."
        )

    target_slot = frappe.get_doc("Yard Slot", target_slot.name)
    if target_slot.status != "Available" or target_slot.current_container:
        frappe.throw(
            f"Destination slot {target_slot.name} is not available."
        )

    movement = frappe.get_doc({
        "doctype": "Container Movement",
        "naming_series": "CM.YY.-.######",
        "container": container.name,
        "movement_type": "Gate In",
        "terminal": terminal.name,
        "to_slot": target_slot.name,
        "movement_time": add_days(now_datetime(), -2),
        "reason": "Discharge",
        "reference_number": f"DEMO-{data['num'][-4:]}",
        "operator": frappe.session.user,
        "notes": "Initial Gate In for Terminal Next demo data.",
    })

    movement.insert()
    movement.submit()

    print(
        f"Submitted Gate In: {container.name} -> {target_slot.name} "
        f"({movement.name})"
    )
    return movement.name


def verify_demo_data(containers, slots, terminal):
    errors = []

    for data in CONTAINERS:
        container = containers[data["num"]]

        if data["status"] == "Expected":
            if (
                container.operational_status != "Expected"
                or container.current_terminal
                or container.current_yard_slot
            ):
                errors.append(
                    f"{container.name} should be Expected and outside the yard."
                )
            continue

        slot = slots[data["slot_idx"]]
        # Reload both records after movement submission.
        container.reload()
        slot.reload()

        if container.operational_status != "In Yard":
            errors.append(f"{container.name} is not In Yard.")

        if container.current_terminal != terminal.name:
            errors.append(f"{container.name} has the wrong terminal.")

        if container.current_yard_slot != slot.name:
            errors.append(f"{container.name} has the wrong current slot.")

        if slot.current_container != container.name:
            errors.append(f"{slot.name} does not point to {container.name}.")

    if errors:
        frappe.throw(
            "Demo-data verification failed:\n- " + "\n- ".join(errors)
        )


def create_demo_data():
    print("Starting Terminal Next demo data generation...")

    company = get_or_create_company()
    shipping_line = get_or_create_shipping_line()
    terminal = get_or_create_terminal(company)
    area = get_or_create_area(terminal)
    block = get_or_create_block(terminal, area)
    slots = get_or_create_slots(terminal, area, block)

    containers = get_or_create_containers(shipping_line, slots, terminal)

    for data in CONTAINERS:
        if data["status"] != "In Yard":
            continue

        target_slot = slots[data["slot_idx"]]
        container = containers[data["num"]]

        create_gate_in_if_needed(
            data=data,
            container=container,
            target_slot=target_slot,
            terminal=terminal,
        )

    # Reload containers before checking the final state.
    for container in containers.values():
        container.reload()

    verify_demo_data(containers, slots, terminal)

    frappe.db.commit()
    frappe.clear_cache()

    print("Terminal Next demo data generated and verified successfully.")
    print(f"Terminal: {terminal.name}")
    print(f"Terminal Area: {area.name}")
    print(f"Yard Block: {block.name}")
    print(f"Containers processed: {len(containers)}")
    print("Expected containers: 1")
    print("Containers placed in yard: 3")


if __name__ == "__main__":
    create_demo_data()
