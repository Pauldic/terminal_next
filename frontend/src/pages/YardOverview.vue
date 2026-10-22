
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Badge, Button } from 'frappe-ui'

type Terminal = {
  name: string
  terminal_name: string
  status: number | boolean
}

type TerminalArea = {
  name: string
  area_name: string
  area_code: string
  area_type: string
  status: string
}

type YardBlock = {
  name: string
  block_name: string
  block_code: string
  terminal_area: string
  bays: number
  rows: number
  tiers: number
  status: string
}

type YardSlot = {
  name: string
  slot_code: string
  terminal_area: string
  yard_block: string
  bay: number
  row: number
  tier: number
  status: 'Available' | 'Blocked' | 'Maintenance'
  current_container?: string | null
  container_number?: string | null
  container_status?: string | null
}

type YardOverviewResponse = {
  terminal: Terminal
  areas: TerminalArea[]
  blocks: YardBlock[]
  selected_block: string | null
  slots: YardSlot[]
}

const apiBase = '/api/method/terminal_next.terminal_next.api'

const terminals = ref<Terminal[]>([])
const areas = ref<TerminalArea[]>([])
const blocks = ref<YardBlock[]>([])
const slots = ref<YardSlot[]>([])

const selectedTerminal = ref('')
const selectedArea = ref('')
const selectedBlock = ref('')
const selectedBay = ref<number | null>(null)
const selectedRow = ref<number | null>(null)
const selectedTier = ref(1)

const loadingTerminals = ref(false)
const loadingOverview = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const selectedBlockData = computed(
  () => blocks.value.find((block) => block.name === selectedBlock.value) ?? null,
)

const selectedSlot = computed(
  () =>
    slots.value.find(
      (slot) =>
        slot.bay === selectedBay.value &&
        slot.row === selectedRow.value &&
        slot.tier === selectedTier.value,
    ) ?? null,
)

const bays = computed(() =>
  Array.from(
    { length: Math.max(0, Number(selectedBlockData.value?.bays ?? 0)) },
    (_, index) => index + 1,
  ),
)

const rows = computed(() =>
  Array.from(
    { length: Math.max(0, Number(selectedBlockData.value?.rows ?? 0)) },
    (_, index) => index + 1,
  ),
)

const tiers = computed(() =>
  Array.from(
    { length: Math.max(0, Number(selectedBlockData.value?.tiers ?? 0)) },
    (_, index) => index + 1,
  ),
)

const slotLookup = computed(() => {
  const result = new Map<string, YardSlot>()
  for (const slot of slots.value) {
    result.set(`${slot.bay}:${slot.row}:${slot.tier}`, slot)
  }
  return result
})

const selectedBlockStats = computed(() => {
  const total = slots.value.length
  const occupied = slots.value.filter((slot) => Boolean(slot.current_container)).length
  const blocked = slots.value.filter(
    (slot) => !slot.current_container && slot.status === 'Blocked',
  ).length
  const maintenance = slots.value.filter(
    (slot) => !slot.current_container && slot.status === 'Maintenance',
  ).length

  return {
    total,
    occupied,
    blocked,
    maintenance,
    available: slots.value.filter(
      (slot) => !slot.current_container && slot.status === 'Available',
    ).length,
  }
})

function slotAt(bay: number, row: number, tier = selectedTier.value) {
  return slotLookup.value.get(`${bay}:${row}:${tier}`) ?? null
}

function slotState(slot: YardSlot | null) {
  if (!slot) return 'missing'
  if (slot.current_container) return 'occupied'
  if (slot.status === 'Blocked') return 'blocked'
  if (slot.status === 'Maintenance') return 'maintenance'
  return 'available'
}

function slotLabel(slot: YardSlot | null) {
  if (!slot) return 'No slot record'
  if (slot.current_container) return slot.container_number || slot.current_container
  if (slot.status === 'Blocked') return 'Blocked'
  if (slot.status === 'Maintenance') return 'Maintenance'
  return 'Available'
}

function slotTheme(slot: YardSlot | null) {
  const state = slotState(slot)
  if (state === 'occupied') return 'blue'
  if (state === 'blocked') return 'red'
  if (state === 'maintenance') return 'amber'
  if (state === 'available') return 'green'
  return 'gray'
}

function slotClasses(slot: YardSlot | null, isSelected: boolean) {
  const state = slotState(slot)
  const stateClass =
    state === 'occupied'
      ? 'border-blue-300 bg-blue-50 text-blue-900 hover:bg-blue-100'
      : state === 'blocked'
        ? 'border-red-300 bg-red-50 text-red-900 hover:bg-red-100'
        : state === 'maintenance'
          ? 'border-amber-300 bg-amber-50 text-amber-900 hover:bg-amber-100'
          : state === 'available'
            ? 'border-green-300 bg-green-50 text-green-900 hover:bg-green-100'
            : 'border-gray-200 bg-gray-50 text-gray-400'

  return [
    'flex min-h-20 min-w-24 flex-col items-start justify-between rounded-lg border p-2 text-left transition',
    stateClass,
    isSelected ? 'ring-2 ring-blue-600 ring-offset-2' : '',
  ]
    .filter(Boolean)
    .join(' ')
}

function csrfToken() {
  const win = window as Window & {
    csrf_token?: string
    frappe?: { csrf_token?: string }
  }

  if (win.csrf_token) return win.csrf_token
  if (win.frappe?.csrf_token) return win.frappe.csrf_token

  const match = document.cookie.match(/(?:^|;\s*)(?:csrf_token|csrftoken)=([^;]+)/)
  return match ? decodeURIComponent(match[1]) : ''
}

async function request<T>(url: string): Promise<T> {
  const response = await fetch(url, {
    credentials: 'include',
    headers: { Accept: 'application/json' },
  })

  const payload = await response.json().catch(() => ({}))

  if (!response.ok || payload.exc || payload.exception) {
    throw new Error(
      payload.message ||
        payload._server_messages ||
        payload.exception ||
        `Request failed (${response.status})`,
    )
  }

  return (payload.message ?? payload) as T
}

async function loadTerminals() {
  loadingTerminals.value = true
  errorMessage.value = ''

  try {
    const result = await request<Terminal[]>(
      `${apiBase}.receiving.get_receiving_terminals`,
    )
    terminals.value = result
    if (!selectedTerminal.value && result.length) {
      selectedTerminal.value = result[0].name
    }
    if (!result.length) {
      errorMessage.value = 'No active terminals are available to display.'
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'Could not load terminals.'
  } finally {
    loadingTerminals.value = false
  }
}

async function loadOverview() {
  if (!selectedTerminal.value) {
    areas.value = []
    blocks.value = []
    slots.value = []
    return
  }

  loadingOverview.value = true
  errorMessage.value = ''

  try {
    const params = new URLSearchParams({ terminal: selectedTerminal.value })
    if (selectedArea.value) params.set('terminal_area', selectedArea.value)
    if (selectedBlock.value) params.set('yard_block', selectedBlock.value)

    const result = await request<YardOverviewResponse>(
      `${apiBase}.yard_overview.get_yard_overview?${params.toString()}`,
    )

    areas.value = result.areas
    blocks.value = result.blocks
    slots.value = result.slots

    if (selectedArea.value && !areas.value.some((area) => area.name === selectedArea.value)) {
      selectedArea.value = ''
      selectedBlock.value = ''
      slots.value = []
      return
    }

    if (selectedBlock.value && !blocks.value.some((block) => block.name === selectedBlock.value)) {
      selectedBlock.value = ''
      slots.value = []
      return
    }

    if (selectedBay.value && !bays.value.includes(selectedBay.value)) {
      selectedBay.value = null
    }
    if (selectedRow.value && !rows.value.includes(selectedRow.value)) {
      selectedRow.value = null
    }
    if (selectedTier.value > Number(selectedBlockData.value?.tiers ?? 0)) {
      selectedTier.value = 1
    }
  } catch (error) {
    errorMessage.value =
      error instanceof Error ? error.message : 'Could not load yard overview.'
    areas.value = []
    blocks.value = []
    slots.value = []
  } finally {
    loadingOverview.value = false
  }
}

function selectSlot(slot: YardSlot | null, bay: number, row: number) {
  selectedBay.value = bay
  selectedRow.value = row
  if (slot) selectedTier.value = slot.tier
}

function openInventory() {
  window.location.href = '/tos/inventory'
}

function openRelocation() {
  window.location.href = '/tos/relocation'
}

watch(selectedTerminal, () => {
  selectedArea.value = ''
  selectedBlock.value = ''
  selectedBay.value = null
  selectedRow.value = null
  selectedTier.value = 1
  void loadOverview()
})

watch(selectedArea, () => {
  selectedBlock.value = ''
  selectedBay.value = null
  selectedRow.value = null
  selectedTier.value = 1
  void loadOverview()
})

watch(selectedBlock, () => {
  selectedBay.value = null
  selectedRow.value = null
  selectedTier.value = 1
  void loadOverview()
})

onMounted(loadTerminals)
</script>

<template>
  <div class="min-h-full space-y-6 p-4 md:p-6">
    <header class="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
      <div>
        <h1 class="text-2xl font-semibold text-ink-gray-9">Yard Overview</h1>
        <p class="mt-1 text-sm text-ink-gray-5">
          Inspect yard capacity, locate containers, and review slot availability.
        </p>
      </div>

      <div class="flex flex-wrap gap-2">
        <Button variant="outline" @click="openInventory">Container Inventory</Button>
        <Button variant="solid" @click="openRelocation">Relocate Container</Button>
      </div>
    </header>

    <div
      v-if="errorMessage"
      class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"
      role="alert"
    >
      {{ errorMessage }}
    </div>

    <div
      v-if="successMessage"
      class="rounded-lg border border-green-200 bg-green-50 p-3 text-sm text-green-800"
    >
      {{ successMessage }}
    </div>

    <section class="grid grid-cols-1 gap-3 rounded-xl border border-outline-gray-2 bg-surface-white p-4 md:grid-cols-3">
      <label class="space-y-1 text-sm">
        <span class="font-medium text-ink-gray-7">Terminal</span>
        <select
          v-model="selectedTerminal"
          class="w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2"
          :disabled="loadingTerminals || !terminals.length"
        >
          <option value="">Select terminal</option>
          <option v-for="terminal in terminals" :key="terminal.name" :value="terminal.name">
            {{ terminal.terminal_name }} ({{ terminal.name }})
          </option>
        </select>
      </label>

      <label class="space-y-1 text-sm">
        <span class="font-medium text-ink-gray-7">Terminal Area</span>
        <select
          v-model="selectedArea"
          class="w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2"
          :disabled="!selectedTerminal || loadingOverview"
        >
          <option value="">All areas</option>
          <option v-for="area in areas" :key="area.name" :value="area.name">
            {{ area.area_name }} — {{ area.area_type }}
          </option>
        </select>
      </label>

      <label class="space-y-1 text-sm">
        <span class="font-medium text-ink-gray-7">Yard Block</span>
        <select
          v-model="selectedBlock"
          class="w-full rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2"
          :disabled="!selectedTerminal || loadingOverview || !blocks.length"
        >
          <option value="">Select a block</option>
          <option v-for="block in blocks" :key="block.name" :value="block.name">
            {{ block.block_name }} ({{ block.block_code }})
            {{ block.status !== 'Active' ? `— ${block.status}` : '' }}
          </option>
        </select>
      </label>
    </section>

    <div v-if="loadingOverview" class="rounded-xl border border-outline-gray-2 p-8 text-center text-sm text-ink-gray-5">
      Loading yard layout…
    </div>

    <template v-else-if="selectedBlockData">
      <section class="grid grid-cols-2 gap-3 xl:grid-cols-5">
        <div class="rounded-xl border border-outline-gray-2 bg-surface-white p-4">
          <p class="text-sm text-ink-gray-5">Defined slots</p>
          <p class="mt-1 text-2xl font-semibold">{{ selectedBlockStats.total }}</p>
          <p class="mt-1 text-xs text-ink-gray-5">
            {{ selectedBlockData.bays }} bays · {{ selectedBlockData.rows }} rows · {{ selectedBlockData.tiers }} tiers
          </p>
        </div>
        <div class="rounded-xl border border-outline-gray-2 bg-surface-white p-4">
          <p class="text-sm text-ink-gray-5">Occupied</p>
          <p class="mt-1 text-2xl font-semibold text-blue-700">{{ selectedBlockStats.occupied }}</p>
        </div>
        <div class="rounded-xl border border-outline-gray-2 bg-surface-white p-4">
          <p class="text-sm text-ink-gray-5">Available</p>
          <p class="mt-1 text-2xl font-semibold text-green-700">{{ selectedBlockStats.available }}</p>
        </div>
        <div class="rounded-xl border border-outline-gray-2 bg-surface-white p-4">
          <p class="text-sm text-ink-gray-5">Blocked</p>
          <p class="mt-1 text-2xl font-semibold text-red-700">{{ selectedBlockStats.blocked }}</p>
        </div>
        <div class="rounded-xl border border-outline-gray-2 bg-surface-white p-4">
          <p class="text-sm text-ink-gray-5">Maintenance</p>
          <p class="mt-1 text-2xl font-semibold text-amber-700">{{ selectedBlockStats.maintenance }}</p>
        </div>
      </section>

      <section class="rounded-xl border border-outline-gray-2 bg-surface-white p-4">
        <div class="mb-4 flex flex-col justify-between gap-3 md:flex-row md:items-center">
          <div>
            <h2 class="text-lg font-semibold">{{ selectedBlockData.block_name }}</h2>
            <p class="text-sm text-ink-gray-5">
              {{ selectedBlockData.block_code }} · {{ selectedBlockData.status }}
            </p>
          </div>

          <label class="flex items-center gap-2 text-sm">
            <span class="font-medium text-ink-gray-7">Stack tier</span>
            <select
              v-model.number="selectedTier"
              class="rounded-lg border border-outline-gray-2 bg-surface-white px-3 py-2"
            >
              <option v-for="tier in tiers" :key="tier" :value="tier">
                Tier {{ tier }}
              </option>
            </select>
          </label>
        </div>

        <div class="mb-4 flex flex-wrap gap-3 text-xs text-ink-gray-6">
          <span class="flex items-center gap-1"><span class="h-3 w-3 rounded-sm border border-blue-300 bg-blue-100"></span> Occupied</span>
          <span class="flex items-center gap-1"><span class="h-3 w-3 rounded-sm border border-green-300 bg-green-100"></span> Available</span>
          <span class="flex items-center gap-1"><span class="h-3 w-3 rounded-sm border border-red-300 bg-red-100"></span> Blocked</span>
          <span class="flex items-center gap-1"><span class="h-3 w-3 rounded-sm border border-amber-300 bg-amber-100"></span> Maintenance</span>
          <span class="flex items-center gap-1"><span class="h-3 w-3 rounded-sm border border-gray-200 bg-gray-50"></span> No slot record</span>
        </div>

        <div v-if="!selectedBlockData.bays || !selectedBlockData.rows" class="rounded-lg bg-surface-gray-1 p-4 text-sm text-ink-gray-6">
          This block has no configured bays or rows.
        </div>

        <div v-else class="overflow-x-auto pb-2">
          <div class="inline-block min-w-full">
            <div class="mb-2 flex">
              <div class="w-20 shrink-0"></div>
              <div class="flex gap-2">
                <div
                  v-for="bay in bays"
                  :key="bay"
                  class="w-24 shrink-0 text-center text-xs font-semibold text-ink-gray-5"
                >
                  BAY {{ bay }}
                </div>
              </div>
            </div>

            <div v-for="row in rows" :key="row" class="mb-2 flex items-stretch">
              <div class="flex w-20 shrink-0 items-center text-sm font-semibold text-ink-gray-6">
                ROW {{ row }}
              </div>
              <div class="flex gap-2">
                <button
                  v-for="bay in bays"
                  :key="`${bay}-${row}`"
                  type="button"
                  :class="slotClasses(slotAt(bay, row), selectedBay === bay && selectedRow === row)"
                  :aria-label="`Bay ${bay}, row ${row}, tier ${selectedTier}: ${slotLabel(slotAt(bay, row))}`"
                  @click="selectSlot(slotAt(bay, row), bay, row)"
                >
                  <span class="text-[10px] font-semibold uppercase tracking-wide opacity-70">
                    {{ slotAt(bay, row)?.slot_code || `B${bay}-R${row}-T${selectedTier}` }}
                  </span>
                  <span class="line-clamp-2 text-xs font-semibold">
                    {{ slotLabel(slotAt(bay, row)) }}
                  </span>
                </button>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section class="rounded-xl border border-outline-gray-2 bg-surface-white p-4">
        <div class="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
          <div>
            <h2 class="text-lg font-semibold">Selected yard position</h2>
            <p class="text-sm text-ink-gray-5">
              Select a grid cell to inspect its slot.
            </p>
          </div>
          <Badge v-if="selectedSlot" :theme="slotTheme(selectedSlot)">
            {{ slotState(selectedSlot) }}
          </Badge>
        </div>

        <div v-if="selectedSlot" class="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <div>
            <p class="text-xs text-ink-gray-5">Slot code</p>
            <p class="font-medium">{{ selectedSlot.slot_code }}</p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">Position</p>
            <p class="font-medium">Bay {{ selectedSlot.bay }} · Row {{ selectedSlot.row }} · Tier {{ selectedSlot.tier }}</p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">Container</p>
            <p class="font-medium">{{ selectedSlot.container_number || selectedSlot.current_container || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">Container status</p>
            <p class="font-medium">{{ selectedSlot.container_status || '—' }}</p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">Slot status</p>
            <p class="font-medium">{{ selectedSlot.status }}</p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">Yard block</p>
            <p class="font-medium">{{ selectedBlockData.block_name }}</p>
          </div>
        </div>

        <div v-else class="mt-4 rounded-lg bg-surface-gray-1 p-4 text-sm text-ink-gray-6">
          No slot selected. Choose a grid cell above to view its details.
        </div>

        <div v-if="selectedSlot?.current_container" class="mt-4 flex flex-wrap gap-2">
          <Button variant="outline" @click="openInventory">Open Container Inventory</Button>
          <Button variant="solid" @click="openRelocation">Relocate Container</Button>
        </div>
      </section>
    </template>

    <section
      v-else-if="selectedTerminal && !loadingOverview"
      class="rounded-xl border border-dashed border-outline-gray-2 bg-surface-white p-8 text-center"
    >
      <h2 class="font-semibold text-ink-gray-8">Select a yard block</h2>
      <p class="mt-1 text-sm text-ink-gray-5">
        Choose a block to load its bay, row, and tier layout.
      </p>
      <p v-if="!blocks.length" class="mt-2 text-sm text-ink-gray-5">
        No yard blocks were found for the selected terminal and area.
      </p>
    </section>
  </div>
</template>
