
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Badge, Button } from 'frappe-ui'

type TerminalOption = {
  name: string
  terminal_name: string
  terminal_code: string
}

type YardSlot = {
  name: string
  slot_code: string
  terminal_area: string
  yard_block: string
  bay: number
  row: number
  tier: number
}

type ContainerDetails = {
  name: string
  container_number: string
  container_type: string
  length_ft: string
  iso_size_type?: string
  tare_weight_kg?: number
  gross_weight_kg?: number
  shipping_line?: string
  seal_number?: string
  operational_status?: string
  current_terminal?: string
  current_yard_slot?: string
}

type ContainerLookup = {
  exists: boolean
  can_receive: boolean
  reason: string | null
  container: ContainerDetails | null
}

type ReceiveResult = {
  success: boolean
  created_container: boolean
  container: string
  container_number: string
  movement: string
  terminal: string
  yard_slot: string
  operational_status: string
}

const API = '/api/method/terminal_next.terminal_next.api.receiving'

const terminals = ref<TerminalOption[]>([])
const slots = ref<YardSlot[]>([])
const selectedTerminal = ref('')
const selectedSlot = ref('')
const containerNumber = ref('')
const reason = ref('Gate-in receiving')

const containerType = ref('Dry')
const lengthFt = ref('20')
const isoSizeType = ref('')
const tareWeight = ref('')
const grossWeight = ref('')
const shippingLine = ref('')
const sealNumber = ref('')
const notes = ref('')

const lookup = ref<ContainerLookup | null>(null)
const result = ref<ReceiveResult | null>(null)
const pageError = ref('')
const lookupError = ref('')
const slotsError = ref('')
const submitting = ref(false)
const loadingTerminals = ref(false)
const loadingSlots = ref(false)
const lookingUp = ref(false)

const isNewContainer = computed(() => lookup.value?.exists === false)
const existingContainer = computed(() => lookup.value?.container ?? null)

const canSubmit = computed(() => {
  if (!selectedTerminal.value || !selectedSlot.value) return false
  if (!lookup.value || !lookup.value.can_receive) return false
  if (submitting.value) return false

  if (isNewContainer.value) {
    if (!containerNumber.value.trim()) return false
    if (!containerType.value || !lengthFt.value) return false
  }

  return true
})

async function request<T>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const response = await fetch(`${API}.${path}`, {
    credentials: 'same-origin',
    ...options,
  })

  const payload = await response.json().catch(() => ({}))

  if (!response.ok || payload.exc) {
    let message =
      payload.message ||
      payload._error_message ||
      `Request failed (${response.status})`

    if (payload._server_messages) {
      try {
        const messages = JSON.parse(payload._server_messages)
        message = messages
          .map((item: string) => {
            try {
              return JSON.parse(item).message
            } catch {
              return item
            }
          })
          .filter(Boolean)
          .join('\n') || message
      } catch {
        // Keep the original error message.
      }
    }

    throw new Error(message)
  }

  return payload.message as T
}

function getCsrfToken(): string {
  const boot = window as Window & {
    csrf_token?: string
    frappe?: { csrf_token?: string }
  }

  if (boot.csrf_token) return boot.csrf_token
  if (boot.frappe?.csrf_token) return boot.frappe.csrf_token

  const cookie = document.cookie
    .split('; ')
    .find((item) => /^(csrf_token|csrftoken)=/.test(item))

  return cookie ? decodeURIComponent(cookie.split('=').slice(1).join('=')) : ''
}

function postForm<T>(path: string, values: Record<string, string>): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
  }

  const token = getCsrfToken()
  if (token) headers['X-Frappe-CSRF-Token'] = token

  return request<T>(path, {
    method: 'POST',
    headers,
    body: new URLSearchParams(values),
  })
}

async function loadTerminals() {
  loadingTerminals.value = true
  pageError.value = ''

  try {
    terminals.value = await request<TerminalOption[]>(
      'get_receiving_terminals',
    )

    if (terminals.value.length === 1) {
      selectedTerminal.value = terminals.value[0].name
    }
  } catch (error) {
    pageError.value =
      error instanceof Error ? error.message : 'Could not load terminals.'
  } finally {
    loadingTerminals.value = false
  }
}

async function loadSlots() {
  slots.value = []
  selectedSlot.value = ''
  slotsError.value = ''

  if (!selectedTerminal.value) return

  loadingSlots.value = true

  try {
    slots.value = await request<YardSlot[]>(
      `get_available_yard_slots?terminal=${encodeURIComponent(selectedTerminal.value)}`,
    )
  } catch (error) {
    slotsError.value =
      error instanceof Error ? error.message : 'Could not load yard slots.'
  } finally {
    loadingSlots.value = false
  }
}

watch(selectedTerminal, () => {
  void loadSlots()
  result.value = null
})

function clearContainerDetails() {
  lookup.value = null
  lookupError.value = ''
  result.value = null
  containerType.value = 'Dry'
  lengthFt.value = '20'
  isoSizeType.value = ''
  tareWeight.value = ''
  grossWeight.value = ''
  shippingLine.value = ''
  sealNumber.value = ''
  notes.value = ''
}

async function lookupContainer() {
  const number = containerNumber.value.trim().toUpperCase().replace(/\s/g, '')

  if (!number) {
    lookupError.value = 'Enter a container number first.'
    lookup.value = null
    return
  }

  containerNumber.value = number
  lookingUp.value = true
  lookupError.value = ''
  result.value = null
  lookup.value = null

  try {
    const data = await request<ContainerLookup>(
      `lookup_container?container_number=${encodeURIComponent(number)}`,
    )

    lookup.value = data

    if (data.exists && data.container) {
      const container = data.container
      containerType.value = container.container_type || 'Dry'
      lengthFt.value = String(container.length_ft || '20')
      isoSizeType.value = container.iso_size_type || ''
      tareWeight.value = String(container.tare_weight_kg ?? '')
      grossWeight.value = String(container.gross_weight_kg ?? '')
      shippingLine.value = container.shipping_line || ''
      sealNumber.value = container.seal_number || ''
      notes.value = ''
    }
  } catch (error) {
    lookupError.value =
      error instanceof Error ? error.message : 'Container lookup failed.'
  } finally {
    lookingUp.value = false
  }
}

async function receiveContainer() {
  if (!canSubmit.value) return

  submitting.value = true
  pageError.value = ''
  result.value = null

  const values: Record<string, string> = {
    container_number: containerNumber.value.trim().toUpperCase(),
    terminal: selectedTerminal.value,
    to_slot: selectedSlot.value,
    reason: reason.value.trim() || 'Gate-in receiving',
  }

  if (isNewContainer.value) {
    values.container_type = containerType.value
    values.length_ft = lengthFt.value
    values.iso_size_type = isoSizeType.value
    values.tare_weight_kg = tareWeight.value
    values.gross_weight_kg = grossWeight.value
    values.shipping_line = shippingLine.value
    values.seal_number = sealNumber.value
    values.notes = notes.value
  }

  try {
    result.value = await postForm<ReceiveResult>('receive_container', values)
    lookup.value = null
    containerNumber.value = ''
    selectedSlot.value = ''
    clearContainerDetails()
    await loadSlots()
  } catch (error) {
    pageError.value =
      error instanceof Error ? error.message : 'Container receiving failed.'
  } finally {
    submitting.value = false
  }
}

function resetForm() {
  containerNumber.value = ''
  selectedSlot.value = ''
  reason.value = 'Gate-in receiving'
  clearContainerDetails()
  pageError.value = ''
  slotsError.value = ''
}

onMounted(() => {
  void loadTerminals()
})
</script>

<template>
  <div class="min-h-full bg-surface-gray-1">
    <div class="mx-auto max-w-5xl space-y-6 px-4 py-6 sm:px-6">
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p class="text-sm text-ink-gray-5">Yard Operations / Receiving</p>
          <h1 class="mt-1 text-2xl font-semibold text-ink-gray-9">
            Container Receiving
          </h1>
          <p class="mt-2 max-w-2xl text-sm text-ink-gray-6">
            Register a new container or receive an eligible existing container
            into an available yard slot.
          </p>
        </div>
        <Badge theme="blue" label="Gate In" />
      </header>

      <div
        v-if="pageError"
        role="alert"
        class="rounded-lg border border-outline-red-1 bg-surface-red-1 px-4 py-3 text-sm text-ink-red-3"
      >
        {{ pageError }}
      </div>

      <div
        v-if="result"
        role="status"
        class="rounded-lg border border-outline-green-1 bg-surface-green-1 p-4"
      >
        <div class="flex items-start gap-3">
          <span class="lucide-check-circle mt-0.5 size-5 text-ink-green-3" />
          <div class="min-w-0 flex-1">
            <h2 class="font-semibold text-ink-green-3">
              Container received successfully
            </h2>
            <p class="mt-1 text-sm text-ink-gray-7">
              {{ result.container_number }} is now recorded as
              {{ result.operational_status }}.
            </p>
            <dl class="mt-3 grid gap-2 text-sm sm:grid-cols-3">
              <div>
                <dt class="text-ink-gray-5">Container record</dt>
                <dd class="font-medium text-ink-gray-8">{{ result.container }}</dd>
              </div>
              <div>
                <dt class="text-ink-gray-5">Movement reference</dt>
                <dd class="font-medium text-ink-gray-8">{{ result.movement }}</dd>
              </div>
              <div>
                <dt class="text-ink-gray-5">Destination slot</dt>
                <dd class="font-medium text-ink-gray-8">{{ result.yard_slot }}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>

      <section class="rounded-xl border border-outline-gray-2 bg-surface-white">
        <div class="border-b border-outline-gray-1 px-5 py-4">
          <h2 class="font-semibold text-ink-gray-9">1. Receiving details</h2>
          <p class="mt-1 text-sm text-ink-gray-5">
            Choose the terminal and identify the arriving container.
          </p>
        </div>

        <div class="grid gap-5 p-5 sm:grid-cols-2">
          <div class="space-y-1.5">
            <label for="terminal" class="text-sm font-medium text-ink-gray-8">
              Terminal <span class="text-ink-red-3">*</span>
            </label>
            <select
              id="terminal"
              v-model="selectedTerminal"
              :disabled="loadingTerminals || submitting"
              class="w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2.5 text-sm text-ink-gray-8 outline-none focus:border-outline-gray-4"
            >
              <option value="">
                {{ loadingTerminals ? 'Loading terminals…' : 'Select terminal' }}
              </option>
              <option
                v-for="terminal in terminals"
                :key="terminal.name"
                :value="terminal.name"
              >
                {{ terminal.terminal_name }} ({{ terminal.terminal_code }})
              </option>
            </select>
            <p
              v-if="!loadingTerminals && !terminals.length && !pageError"
              class="text-xs text-ink-gray-5"
            >
              No active terminals are available to your account.
            </p>
          </div>

          <div class="space-y-1.5">
            <label for="container-number" class="text-sm font-medium text-ink-gray-8">
              Container number <span class="text-ink-red-3">*</span>
            </label>
            <div class="flex gap-2">
              <input
                id="container-number"
                v-model="containerNumber"
                autocomplete="off"
                placeholder="e.g. ABCD1234567"
                :disabled="submitting"
                class="min-w-0 flex-1 rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2.5 text-sm uppercase text-ink-gray-8 outline-none placeholder:normal-case focus:border-outline-gray-4"
                @keydown.enter.prevent="lookupContainer"
              />
              <Button
                label="Look up"
                :loading="lookingUp"
                :disabled="!containerNumber.trim() || submitting"
                @click="lookupContainer"
              />
            </div>
            <p class="text-xs text-ink-gray-5">
              Look up the container before receiving it.
            </p>
          </div>
        </div>
      </section>

      <section
        v-if="lookup"
        class="rounded-xl border border-outline-gray-2 bg-surface-white"
      >
        <div class="flex flex-wrap items-start justify-between gap-3 border-b border-outline-gray-1 px-5 py-4">
          <div>
            <h2 class="font-semibold text-ink-gray-9">
              2. Container information
            </h2>
            <p class="mt-1 text-sm text-ink-gray-5">
              {{ containerNumber }}
            </p>
          </div>
          <Badge
            v-if="lookup.exists"
            :theme="lookup.can_receive ? 'green' : 'red'"
            :label="lookup.container?.operational_status || 'Existing container'"
          />
          <Badge v-else theme="blue" label="New container" />
        </div>

        <div class="space-y-5 p-5">
          <div
            v-if="lookupError"
            class="rounded-lg border border-outline-red-1 bg-surface-red-1 px-3 py-2 text-sm text-ink-red-3"
          >
            {{ lookupError }}
          </div>

          <div
            v-if="!lookup.can_receive"
            role="alert"
            class="rounded-lg border border-outline-red-1 bg-surface-red-1 px-4 py-3 text-sm text-ink-red-3"
          >
            {{ lookup.reason || 'This container cannot be received.' }}
          </div>

          <template v-if="lookup.exists && existingContainer">
            <div class="grid gap-4 sm:grid-cols-3">
              <div>
                <p class="text-xs text-ink-gray-5">Container number</p>
                <p class="mt-1 font-medium text-ink-gray-9">
                  {{ existingContainer.container_number }}
                </p>
              </div>
              <div>
                <p class="text-xs text-ink-gray-5">Type</p>
                <p class="mt-1 font-medium text-ink-gray-9">
                  {{ existingContainer.container_type || 'Not specified' }}
                </p>
              </div>
              <div>
                <p class="text-xs text-ink-gray-5">Length</p>
                <p class="mt-1 font-medium text-ink-gray-9">
                  {{ existingContainer.length_ft || '—' }} ft
                </p>
              </div>
              <div>
                <p class="text-xs text-ink-gray-5">Shipping line</p>
                <p class="mt-1 font-medium text-ink-gray-9">
                  {{ existingContainer.shipping_line || 'Not specified' }}
                </p>
              </div>
              <div>
                <p class="text-xs text-ink-gray-5">Seal number</p>
                <p class="mt-1 font-medium text-ink-gray-9">
                  {{ existingContainer.seal_number || 'Not specified' }}
                </p>
              </div>
              <div>
                <p class="text-xs text-ink-gray-5">ISO size/type</p>
                <p class="mt-1 font-medium text-ink-gray-9">
                  {{ existingContainer.iso_size_type || 'Not specified' }}
                </p>
              </div>
            </div>
            <p class="text-xs text-ink-gray-5">
              Existing container details are displayed for review. Edit them
              through the Container record if corrections are required.
            </p>
          </template>

          <template v-else-if="!lookup.exists">
            <p class="text-sm text-ink-gray-6">
              No existing record was found. Enter the container details to
              register it as part of receiving.
            </p>

            <div class="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              <div class="space-y-1.5">
                <label for="container-type" class="text-sm font-medium text-ink-gray-8">
                  Container type <span class="text-ink-red-3">*</span>
                </label>
                <select id="container-type" v-model="containerType" class="field">
                  <option>Dry</option>
                  <option>Reefer</option>
                  <option>Open Top</option>
                  <option>Flat Rack</option>
                  <option>Tank</option>
                  <option>Other</option>
                </select>
              </div>

              <div class="space-y-1.5">
                <label for="length-ft" class="text-sm font-medium text-ink-gray-8">
                  Length <span class="text-ink-red-3">*</span>
                </label>
                <select id="length-ft" v-model="lengthFt" class="field">
                  <option value="20">20 ft</option>
                  <option value="40">40 ft</option>
                  <option value="45">45 ft</option>
                </select>
              </div>

              <div class="space-y-1.5">
                <label for="iso-size" class="text-sm font-medium text-ink-gray-8">
                  ISO size/type
                </label>
                <input id="iso-size" v-model="isoSizeType" placeholder="e.g. 22G1" class="field" />
              </div>

              <div class="space-y-1.5">
                <label for="tare-weight" class="text-sm font-medium text-ink-gray-8">
                  Tare weight (kg)
                </label>
                <input id="tare-weight" v-model="tareWeight" type="number" min="0" step="any" placeholder="Optional" class="field" />
              </div>

              <div class="space-y-1.5">
                <label for="gross-weight" class="text-sm font-medium text-ink-gray-8">
                  Gross weight (kg)
                </label>
                <input id="gross-weight" v-model="grossWeight" type="number" min="0" step="any" placeholder="Optional" class="field" />
              </div>

              <div class="space-y-1.5">
                <label for="shipping-line" class="text-sm font-medium text-ink-gray-8">
                  Shipping line (Customer ID)
                </label>
                <input id="shipping-line" v-model="shippingLine" placeholder="ERPNext Customer ID" class="field" />
              </div>

              <div class="space-y-1.5">
                <label for="seal-number" class="text-sm font-medium text-ink-gray-8">
                  Seal number
                </label>
                <input id="seal-number" v-model="sealNumber" placeholder="Optional" class="field" />
              </div>

              <div class="space-y-1.5 sm:col-span-2">
                <label for="container-notes" class="text-sm font-medium text-ink-gray-8">
                  Notes
                </label>
                <textarea id="container-notes" v-model="notes" rows="2" placeholder="Additional container details" class="field" />
              </div>
            </div>
          </template>
        </div>
      </section>

      <section
        v-if="lookup?.can_receive"
        class="rounded-xl border border-outline-gray-2 bg-surface-white"
      >
        <div class="border-b border-outline-gray-1 px-5 py-4">
          <h2 class="font-semibold text-ink-gray-9">3. Yard placement</h2>
          <p class="mt-1 text-sm text-ink-gray-5">
            Choose an available slot for this container.
          </p>
        </div>

        <div class="grid gap-5 p-5 sm:grid-cols-2">
          <div class="space-y-1.5">
            <label for="yard-slot" class="text-sm font-medium text-ink-gray-8">
              Destination yard slot <span class="text-ink-red-3">*</span>
            </label>
            <select
              id="yard-slot"
              v-model="selectedSlot"
              :disabled="!selectedTerminal || loadingSlots || submitting"
              class="field"
            >
              <option value="">
                {{ loadingSlots ? 'Loading slots…' : 'Select available slot' }}
              </option>
              <option v-for="slot in slots" :key="slot.name" :value="slot.name">
                {{ slot.slot_code }} — {{ slot.yard_block }},
                Bay {{ slot.bay }}, Row {{ slot.row }}, Tier {{ slot.tier }}
              </option>
            </select>
            <p v-if="slotsError" class="text-sm text-ink-red-3">
              {{ slotsError }}
            </p>
            <p v-else-if="!loadingSlots && selectedTerminal && !slots.length" class="text-xs text-ink-gray-5">
              No available slots were found for this terminal.
            </p>
          </div>

          <div class="space-y-1.5">
            <label for="receiving-reason" class="text-sm font-medium text-ink-gray-8">
              Receiving reason
            </label>
            <input
              id="receiving-reason"
              v-model="reason"
              placeholder="Gate-in receiving"
              class="field"
            />
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-3 border-t border-outline-gray-1 px-5 py-4">
          <p class="max-w-xl text-xs text-ink-gray-5">
            Submitting creates and submits a Gate In Container Movement.
            Container location is updated by the backend movement workflow.
          </p>
          <div class="flex gap-2">
            <Button label="Reset" :disabled="submitting" @click="resetForm" />
            <Button
              label="Receive container"
              variant="solid"
              :loading="submitting"
              :disabled="!canSubmit"
              @click="receiveContainer"
            />
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.field {
  width: 100%;
  border: 1px solid var(--outline-gray-2);
  border-radius: 0.5rem;
  background: var(--surface-white);
  padding: 0.625rem 0.75rem;
  font-size: 0.875rem;
  color: var(--ink-gray-8);
  outline: none;
}

.field:focus {
  border-color: var(--outline-gray-4);
}

.field:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
