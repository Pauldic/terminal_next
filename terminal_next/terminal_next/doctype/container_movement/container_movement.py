
# container_movement.py
import frappe
from frappe.model.document import Document
from frappe.utils import get_datetime


class ContainerMovement(Document):
    def validate(self):
        if self.docstatus == 2:
            return

        container = frappe.db.get_value(
            "Container",
            self.container,
            [
                "current_terminal",
                "current_yard_slot",
                "operational_status",
            ],
            as_dict=True,
        )

        if not container:
            frappe.throw("Select a valid Container.")

        if not frappe.db.exists("Terminal", self.terminal):
            frappe.throw("Select a valid Terminal.")

        if (
            self.movement_time
            and get_datetime(self.movement_time) > get_datetime()
        ):
            frappe.throw("Movement Time cannot be in the future.")

        if self.movement_type == "Adjustment":
            self._validate_adjustment(container)
        else:
            self._validate_standard_movement(container)

        # A draft may be submitted for the first time. Reject changes only
        # when the database already contains this movement as submitted.
        if not self.is_new():
            saved_docstatus = frappe.db.get_value(
                self.doctype,
                self.name,
                "docstatus",
            )

            if saved_docstatus == 1:
                frappe.throw(
                    "Submitted Container Movements cannot be edited."
                )

    def _validate_standard_movement(self, container):
        if self.movement_type == "Gate In":
            if self.from_slot:
                frappe.throw("Gate In must not have a source slot.")
            if not self.to_slot:
                frappe.throw("Gate In requires a destination slot.")
            if container.current_yard_slot:
                frappe.throw(
                    "This container is already in the yard. "
                    "Use Yard Transfer or Gate Out."
                )

        elif self.movement_type == "Gate Out":
            if not self.from_slot:
                frappe.throw("Gate Out requires a source slot.")
            if self.to_slot:
                frappe.throw("Gate Out must not have a destination slot.")

        elif self.movement_type == "Yard Transfer":
            if not self.from_slot or not self.to_slot:
                frappe.throw(
                    "Yard Transfer requires both source and destination slots."
                )
            if self.from_slot == self.to_slot:
                frappe.throw(
                    "Source and destination slots must be different."
                )

        else:
            frappe.throw("Unsupported movement type.")

        if (
            self.movement_type in ("Yard Transfer", "Gate Out")
            and container.current_terminal
            and container.current_terminal != self.terminal
        ):
            frappe.throw(
                "Container's current terminal does not match "
                "this movement's terminal."
            )

        if self.from_slot:
            source = self._get_slot(self.from_slot, "Source")

            if source.terminal != self.terminal:
                frappe.throw(
                    "Source slot must belong to the selected Terminal."
                )

            if source.current_container != self.container:
                frappe.throw(
                    "The source slot does not currently contain this container."
                )

            if container.current_yard_slot != self.from_slot:
                frappe.throw(
                    "The source slot differs from the container's recorded "
                    "location. Use an Adjustment to reconcile the discrepancy."
                )

        if self.to_slot:
            destination = self._get_slot(self.to_slot, "Destination")

            if destination.terminal != self.terminal:
                frappe.throw(
                    "Destination slot must belong to the selected Terminal."
                )

            if destination.status != "Available":
                frappe.throw("Destination slot is not available.")

            if destination.current_container:
                frappe.throw("Destination slot is already occupied.")

    def _validate_adjustment(self, container):
        mode = self.adjustment_mode

        if not mode:
            frappe.throw(
                "Adjustment Mode is required for an Adjustment movement."
            )

        if not (self.reason or "").strip():
            frappe.throw("A reason is required for an Adjustment movement.")

        if len((self.reconciliation_details or "").strip()) < 15:
            frappe.throw(
                "Provide at least 15 characters explaining the verified "
                "discrepancy and the correction."
            )

        if mode == "Relocate":
            if not self.from_slot or not self.to_slot:
                frappe.throw(
                    "Relocate requires both source and destination slots."
                )

            if self.from_slot == self.to_slot:
                frappe.throw(
                    "Source and destination slots must be different."
                )

            if container.current_yard_slot != self.from_slot:
                frappe.throw(
                    "Relocate requires the source to match the "
                    "container's recorded yard location."
                )

            if (
                container.current_terminal
                and container.current_terminal != self.terminal
            ):
                frappe.throw(
                    "Container's current terminal does not match "
                    "this movement's terminal."
                )

        elif mode == "Place in Yard":
            if self.from_slot:
                frappe.throw(
                    "Place in Yard must not specify a source slot."
                )

            if not self.to_slot:
                frappe.throw("Place in Yard requires a destination slot.")

            if container.current_yard_slot:
                frappe.throw(
                    "The container already has a recorded yard slot. "
                    "Use Correct Recorded Location if the record is wrong."
                )

        elif mode == "Remove from Yard":
            if self.to_slot:
                frappe.throw(
                    "Remove from Yard must not specify a destination slot."
                )

            if not self.from_slot and not container.current_yard_slot:
                frappe.throw(
                    "Remove from Yard requires a source slot or "
                    "a recorded location."
                )

            if (
                self.from_slot
                and container.current_yard_slot != self.from_slot
            ):
                frappe.throw(
                    "The source must match the recorded location. "
                    "Use Correct Recorded Location to reconcile a discrepancy."
                )

            if (
                container.current_terminal
                and container.current_terminal != self.terminal
            ):
                frappe.throw(
                    "Container's current terminal does not match "
                    "this movement's terminal."
                )

        elif mode == "Correct Recorded Location":
            if not self.to_slot:
                frappe.throw(
                    "Correct Recorded Location requires a verified "
                    "destination slot."
                )

            if self.from_slot and self.from_slot == self.to_slot:
                frappe.throw(
                    "Source and destination slots must be different."
                )

        else:
            frappe.throw("Unsupported Adjustment Mode.")

        # Validate explicitly supplied slots.
        if self.from_slot:
            source = self._get_slot(self.from_slot, "Source")

            if source.terminal != self.terminal:
                frappe.throw(
                    "Source slot must belong to the selected Terminal."
                )

            if source.current_container != self.container:
                frappe.throw(
                    "The source slot does not currently contain this container."
                )

        if self.to_slot:
            destination = self._get_slot(self.to_slot, "Destination")

            if destination.terminal != self.terminal:
                frappe.throw(
                    "Destination slot must belong to the selected Terminal."
                )

            if destination.status != "Available":
                frappe.throw("Destination slot is not available.")

            # An Adjustment may use the same container's verified
            # destination, but must never overwrite another container.
            if (
                destination.current_container
                and destination.current_container != self.container
            ):
                frappe.throw("Destination slot is already occupied.")

    def _get_slot(self, slot_name, label):
        slot = frappe.db.get_value(
            "Yard Slot",
            slot_name,
            ["terminal", "status", "current_container"],
            as_dict=True,
        )

        if not slot:
            frappe.throw(f"{label} Yard Slot does not exist.")

        return slot

    def on_submit(self):
        # Serialize movements involving the same container.
        frappe.db.sql(
            """
            SELECT name
            FROM `tabContainer`
            WHERE name = %s
            FOR UPDATE
            """,
            (self.container,),
        )

        container = frappe.db.get_value(
            "Container",
            self.container,
            [
                "current_terminal",
                "current_yard_slot",
                "operational_status",
            ],
            as_dict=True,
        )

        if not container:
            frappe.throw("Container no longer exists. Reload and retry.")

        # Lock every relevant slot in a consistent order. Include the
        # recorded slot so reconciliation can inspect it safely.
        slot_names = {
            slot
            for slot in (
                self.from_slot,
                self.to_slot,
                container.current_yard_slot
                if self.movement_type == "Adjustment"
                else None,
            )
            if slot
        }

        for slot_name in sorted(slot_names):
            frappe.db.sql(
                """
                SELECT name
                FROM `tabYard Slot`
                WHERE name = %s
                FOR UPDATE
                """,
                (slot_name,),
            )

        # Re-read slot and container state after obtaining the locks.
        container = frappe.db.get_value(
            "Container",
            self.container,
            [
                "current_terminal",
                "current_yard_slot",
                "operational_status",
            ],
            as_dict=True,
        )

        if not container:
            frappe.throw("Container no longer exists. Reload and retry.")

        slots = {}
        for slot_name in sorted(slot_names):
            slots[slot_name] = frappe.db.get_value(
                "Yard Slot",
                slot_name,
                ["terminal", "status", "current_container"],
                as_dict=True,
            )

            if not slots[slot_name]:
                frappe.throw(
                    f"Yard Slot {slot_name} no longer exists. Reload and retry."
                )

        # Determine the actual inventory changes.
        source_names = set()
        destination_name = self.to_slot or None

        if self.movement_type == "Adjustment":
            mode = self.adjustment_mode

            if mode == "Relocate":
                source_names.add(self.from_slot)

            elif mode == "Place in Yard":
                if container.current_yard_slot:
                    frappe.throw(
                        "Container already has a recorded yard location."
                    )

            elif mode == "Remove from Yard":
                source_name = self.from_slot or container.current_yard_slot

                if not source_name:
                    frappe.throw("No source location is available to remove.")

                source_names.add(source_name)
                destination_name = None

            elif mode == "Correct Recorded Location":
                # Clear only slots that actually contain this container.
                # Never clear another container's valid occupancy.
                if self.from_slot:
                    source_names.add(self.from_slot)

                recorded_slot = container.current_yard_slot
                if recorded_slot and recorded_slot in slots:
                    if (
                        slots[recorded_slot].current_container
                        == self.container
                    ):
                        source_names.add(recorded_slot)

        elif self.movement_type == "Gate In":
            if container.current_yard_slot:
                frappe.throw(
                    "Container is already in the yard. Reload and retry."
                )

        elif self.movement_type in ("Yard Transfer", "Gate Out"):
            if container.current_yard_slot != self.from_slot:
                frappe.throw(
                    "Container location changed before submission. "
                    "Reload and retry."
                )

            source_names.add(self.from_slot)

            if (
                container.current_terminal
                and container.current_terminal != self.terminal
            ):
                frappe.throw(
                    "Container's terminal changed before submission. "
                    "Reload and retry."
                )

        else:
            frappe.throw("Unsupported movement type.")

        # Verify every source before modifying anything.
        for source_name in source_names:
            source = slots.get(source_name)

            if not source or source.current_container != self.container:
                frappe.throw(
                    f"Source slot {source_name} no longer contains this "
                    "container. Reload and reconcile the inventory."
                )

        # Revalidate destination after locking it.
        if destination_name:
            destination = slots.get(destination_name)

            if not destination:
                frappe.throw(
                    "Destination slot no longer exists. Reload and retry."
                )

            if destination.terminal != self.terminal:
                frappe.throw(
                    "Destination slot belongs to a different terminal."
                )

            if destination.status != "Available":
                frappe.throw(
                    "Destination slot is no longer available. Reload and retry."
                )

            if (
                destination.current_container
                and destination.current_container != self.container
            ):
                frappe.throw(
                    "Destination slot is occupied by another container."
                )

        # Validate terminal ownership for sources.
        for source_name in source_names:
            if slots[source_name].terminal != self.terminal:
                frappe.throw(
                    "Source slot belongs to a different terminal."
                )

        # Apply all slot changes only after all checks pass.
        for source_name in source_names:
            if source_name != destination_name:
                frappe.db.set_value(
                    "Yard Slot",
                    source_name,
                    "current_container",
                    None,
                    update_modified=False,
                )

        if destination_name:
            frappe.db.set_value(
                "Yard Slot",
                destination_name,
                "current_container",
                self.container,
                update_modified=False,
            )

        # Refresh the container's authoritative location.
        if destination_name:
            frappe.db.set_value(
                "Container",
                self.container,
                {
                    "current_terminal": self.terminal,
                    "current_yard_slot": destination_name,
                    "operational_status": "In Yard",
                },
                update_modified=False,
            )
        else:
            frappe.db.set_value(
                "Container",
                self.container,
                {
                    "current_terminal": None,
                    "current_yard_slot": None,
                    "operational_status": "Out-Gated",
                },
                update_modified=False,
            )

    def on_cancel(self):
        frappe.throw(
            "Submitted Container Movements cannot be cancelled because "
            "inventory changes are audited. Create a new Adjustment "
            "movement to correct the position."
        )
