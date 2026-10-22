
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Badge, Button } from 'frappe-ui'

type ContainerRow = {
  name: string
  container_number: string
  container_type?: string
  length_ft?: number
  operational_status: string
  current_terminal?: string
  current_yard_slot?: string
  shipping_line?: string
}

type TerminalOption = {
  name: string
  terminal_name: string
  terminal_code?: string
}

type YardSlot = {
  name: string
  slot_code: string
  terminal_area?: string
  yard_block?: string
  bay?: string
  row?: string
  tier?: string
}

const apiBase = '/api/method/terminal_next.terminal_next.api'

const searchInput = ref('')
const containers = ref<ContainerRow[]>([])
const selectedContainerName = ref('')
const terminals = ref<TerminalOption[]>([])
const slots = ref<YardSlot[]>([])
const selectedSlot = ref('')
const reason = ref('Relocation')
const notes = ref('')
const referenceNumber = ref('')

const loadingContainers = ref(false)
const loadingSlots = ref(false)
const submitting = ref(false)
const errorMessage = ref('')
const successMessage = ref('')
const movementReference = ref('')

const selectedContainer = computed(
  () => containers.value.find((item) => item.name === selectedContainerName.value) ?? null,
)

const destinationOptions = computed(() =>
  slots.value.filter((slot) => slot.name !== selectedContainer.value?.current_yard_slot),
)

function getCsrfToken(): string {
  const frappeWindow = window as Window & {
    csrf_token?: string
    frappe?: { csrf_token?: string }
  }

  if (frappeWindow.csrf_token) return frappeWindow.csrf_token
  if (frappeWindow.frappe?.csrf_token) return frappeWindow.frappe.csrf_token

  const cookie = document.cookie
    .split('; ')
    .find((item) => item.startsWith('csrf_token=') || item.startsWith('csrftoken='))

  return cookie ? decodeURIComponent(cookie.substring(cookie.indexOf('=') + 1)) : ''
}

async function apiGet<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${apiBase}${endpoint}`, {
    credentials: 'include',
  })

  const payload = await response.json()

  if (!response.ok || payload.exc || payload.exception) {
    throw new Error(payload._error_message || 'The request failed.')
  }

  return payload.message as T
}

async function apiPost<T>(
  endpoint: string,
  data: Record<string, unknown>,
): Promise<T> {
  const token = getCsrfToken()

  const response = await fetch(`${apiBase}${endpoint}`, {
    method: 'POST',
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { 'X-Frappe-CSRF-Token': token } : {}),
    },
    body: JSON.stringify(data),
  })

  const payload = await response.json()

  if (!response.ok || payload.exc || payload.exception) {
    throw new Error(payload._error_message || 'The request failed.')
  }

  return payload.message as T
}

async function loadTerminals() {
  terminals.value = await apiGet<TerminalOption[]>(
    '.receiving.get_receiving_terminals',
  )
}

async function searchContainers() {
  errorMessage.value = ''
  successMessage.value = ''
  movementReference.value = ''
  loadingContainers.value = true

  try {
    const query = new URLSearchParams({
      search: searchInput.value.trim(),
      operational_status: 'In Yard',
      start: '0',
      page_length: '50',
    })

    const result = await apiGet<{ data: ContainerRow[] }>(
      `.receiving.get_container_inventory?${query.toString()}`,
    )

    containers.value = result.data.filter(
      (item) => item.operational_status === 'In Yard'
        && Boolean(item.current_terminal)
        && Boolean(item.current_yard_slot),
    )

    if (!containers.value.some((item) => item.name === selectedContainerName.value)) {
      selectedContainerName.value = ''
      slots.value = []
      selectedSlot.value = ''
    }
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Unable to search containers.'
  } finally {
    loadingContainers.value = false
  }
}

async function loadDestinationSlots() {
  slots.value = []
  selectedSlot.value = ''
  errorMessage.value = ''

  if (!selectedContainer.value?.current_terminal) return

  loadingSlots.value = true

  try {
    const query = new URLSearchParams({
      terminal: selectedContainer.value.current_terminal,
    })

    slots.value = await apiGet<YardSlot[]>(
      `.receiving.get_available_yard_slots?${query.toString()}`,
    )
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Unable to load destination slots.'
  } finally {
    loadingSlots.value = false
  }
}

watch(selectedContainerName, () => {
  successMessage.value = ''
  movementReference.value = ''
  void loadDestinationSlots()
})

async function submitRelocation() {
  if (!selectedContainer.value || !selectedSlot.value) {
    errorMessage.value = 'Select a container and destination slot.'
    return
  }

  if (selectedSlot.value === selectedContainer.value.current_yard_slot) {
    errorMessage.value = 'Choose a destination different from the current slot.'
    return
  }

  errorMessage.value = ''
  successMessage.value = ''
  movementReference.value = ''
  submitting.value = true

  try {
    const result = await apiPost<{
      success: boolean
      message: string
      movement: string
      container_number: string
      from_slot: string
      to_slot: string
    }>('.relocation.relocate_container', {
      container: selectedContainer.value.name,
      to_slot: selectedSlot.value,
      reason: reason.value,
      notes: notes.value.trim() || undefined,
      reference_number: referenceNumber.value.trim() || undefined,
    })

    movementReference.value = result.movement
    successMessage.value = result.message

    const movedName = selectedContainer.value.name
    containers.value = containers.value.filter((item) => item.name !== movedName)
    selectedContainerName.value = ''
    selectedSlot.value = ''
    slots.value = []
    notes.value = ''
    referenceNumber.value = ''
    searchInput.value = ''

    await searchContainers()
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Relocation failed. Refresh the inventory and try again.'
  } finally {
    submitting.value = false
  }
}

function slotLabel(slot: YardSlot): string {
  const location = [
    slot.terminal_area,
    slot.yard_block,
    slot.bay ? `Bay ${slot.bay}` : '',
    slot.row ? `Row ${slot.row}` : '',
    slot.tier ? `Tier ${slot.tier}` : '',
  ].filter(Boolean).join(' · ')

  return location ? `${slot.slot_code} — ${location}` : slot.slot_code
}

onMounted(async () => {
  try {
    await loadTerminals()
  } catch (error) {
    errorMessage.value = error instanceof Error
      ? error.message
      : 'Unable to load terminals.'
  }
})
</script>

<template>
  <main class="mx-auto w-full max-w-5xl space-y-6 p-4 md:p-6">
    <header class="flex flex-wrap items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold text-ink-gray-9">Container Relocation</h1>
        <p class="mt-1 text-sm text-ink-gray-5">
          Move a container to another available slot within its current terminal.
        </p>
      </div>
      <Button route="/inventory" label="Back to inventory" />
    </header>

    <div
      v-if="errorMessage"
      role="alert"
      class="rounded-lg border border-outline-red-2 bg-surface-red-1 p-3 text-sm text-ink-red-3"
    >
      {{ errorMessage }}
    </div>

    <div
      v-if="successMessage"
      role="status"
      class="rounded-lg border border-outline-green-2 bg-surface-green-1 p-4"
    >
      <p class="font-medium text-ink-green-3">{{ successMessage }}</p>
      <p v-if="movementReference" class="mt-1 text-sm text-ink-gray-7">
        Movement reference: <strong>{{ movementReference }}</strong>
      </p>
    </div>

    <section class="rounded-xl border border-outline-gray-2 bg-surface-white p-5">
      <h2 class="text-base font-semibold text-ink-gray-9">1. Select container</h2>
      <p class="mt-1 text-sm text-ink-gray-5">
        Search by container number or record ID. Only containers currently in the yard are shown.
      </p>

      <form class="mt-4 flex flex-wrap gap-2" @submit.prevent="searchContainers">
        <input
          v-model="searchInput"
          class="min-w-0 flex-1 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm"
          placeholder="Container number or record ID"
        />
        <Button
          type="submit"
          label="Search"
          :loading="loadingContainers"
        />
      </form>

      <div v-if="containers.length" class="mt-4">
        <label for="relocation-container" class="mb-1 block text-sm font-medium text-ink-gray-7">
          Matching containers
        </label>
        <select
          id="relocation-container"
          v-model="selectedContainerName"
          class="w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm"
        >
          <option value="">Choose a container</option>
          <option v-for="item in containers" :key="item.name" :value="item.name">
            {{ item.container_number }} — {{ item.current_yard_slot }}
          </option>
        </select>
      </div>

      <p v-else-if="!loadingContainers" class="mt-3 text-sm text-ink-gray-5">
        Search to find containers eligible for relocation.
      </p>

      <div v-if="selectedContainer" class="mt-4 rounded-lg bg-surface-gray-1 p-4">
        <div class="flex flex-wrap items-center justify-between gap-2">
          <h3 class="font-semibold text-ink-gray-9">
            {{ selectedContainer.container_number }}
          </h3>
          <Badge theme="green" label="In Yard" />
        </div>
        <dl class="mt-3 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt class="text-ink-gray-5">Container record</dt>
            <dd class="font-medium text-ink-gray-8">{{ selectedContainer.name }}</dd>
          </div>
          <div>
            <dt class="text-ink-gray-5">Terminal</dt>
            <dd class="font-medium text-ink-gray-8">
              {{ terminals.find(t => t.name === selectedContainer?.current_terminal)?.terminal_name
                || selectedContainer.current_terminal }}
            </dd>
          </div>
          <div>
            <dt class="text-ink-gray-5">Current slot</dt>
            <dd class="font-medium text-ink-gray-8">{{ selectedContainer.current_yard_slot }}</dd>
          </div>
          <div>
            <dt class="text-ink-gray-5">Container type</dt>
            <dd class="font-medium text-ink-gray-8">
              {{ selectedContainer.container_type || '—' }}
              <span v-if="selectedContainer.length_ft">· {{ selectedContainer.length_ft }} ft</span>
            </dd>
          </div>
        </dl>
      </div>
    </section>

    <section class="rounded-xl border border-outline-gray-2 bg-surface-white p-5">
      <h2 class="text-base font-semibold text-ink-gray-9">2. Choose destination</h2>
      <p class="mt-1 text-sm text-ink-gray-5">
        Only available slots in the container's current terminal are offered.
      </p>

      <div v-if="!selectedContainer" class="mt-4 text-sm text-ink-gray-5">
        Select a container first.
      </div>

      <div v-else class="mt-4">
        <label for="relocation-slot" class="mb-1 block text-sm font-medium text-ink-gray-7">
          Destination yard slot
        </label>
        <select
          id="relocation-slot"
          v-model="selectedSlot"
          :disabled="loadingSlots || !destinationOptions.length"
          class="w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm disabled:opacity-60"
        >
          <option value="">
            {{ loadingSlots ? 'Loading available slots…' : 'Choose a destination slot' }}
          </option>
          <option v-for="slot in destinationOptions" :key="slot.name" :value="slot.name">
            {{ slotLabel(slot) }}
          </option>
        </select>

        <p v-if="!loadingSlots && !destinationOptions.length" class="mt-2 text-sm text-ink-amber-3">
          No available destination slots were found for this terminal.
        </p>
      </div>
    </section>

    <section class="rounded-xl border border-outline-gray-2 bg-surface-white p-5">
      <h2 class="text-base font-semibold text-ink-gray-9">3. Movement details</h2>

      <div class="mt-4 grid gap-4 sm:grid-cols-2">
        <div>
          <label for="relocation-reason" class="mb-1 block text-sm font-medium text-ink-gray-7">
            Reason
          </label>
          <select
            id="relocation-reason"
            v-model="reason"
            class="w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm"
          >
            <option>Relocation</option>
            <option>Discharge</option>
            <option>Receipt</option>
            <option>Delivery</option>
            <option>Inspection</option>
            <option>Reefer Handling</option>
            <option>Correction</option>
            <option>Other</option>
          </select>
        </div>

        <div>
          <label for="relocation-reference" class="mb-1 block text-sm font-medium text-ink-gray-7">
            External reference <span class="font-normal text-ink-gray-5">(optional)</span>
          </label>
          <input
            id="relocation-reference"
            v-model="referenceNumber"
            class="w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm"
            placeholder="Work order or reference"
          />
        </div>

        <div class="sm:col-span-2">
          <label for="relocation-notes" class="mb-1 block text-sm font-medium text-ink-gray-7">
            Notes <span class="font-normal text-ink-gray-5">(optional)</span>
          </label>
          <textarea
            id="relocation-notes"
            v-model="notes"
            rows="3"
            class="w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2 text-sm"
            placeholder="Additional operational details"
          />
        </div>
      </div>

      <div class="mt-5 flex flex-wrap justify-end gap-2">
        <Button route="/inventory" label="Cancel" />
        <Button
          label="Submit relocation"
          variant="solid"
          :loading="submitting"
          :disabled="!selectedContainer || !selectedSlot || loadingSlots"
          @click="submitRelocation"
        />
      </div>
    </section>
  </main>
</template>
