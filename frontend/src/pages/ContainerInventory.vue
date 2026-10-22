
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { Badge, Button } from 'frappe-ui'

type ContainerRow = {
  name: string
  container_number: string
  container_type: string
  length_ft: string
  iso_size_type?: string
  shipping_line?: string
  operational_status: string
  current_terminal?: string
  current_yard_slot?: string
  modified: string
}

type InventoryResponse = {
  data: ContainerRow[]
  start: number
  page_length: number
  has_more: boolean
}

type TerminalOption = {
  name: string
  terminal_name: string
  terminal_code: string
}

const API = '/api/method/terminal_next.terminal_next.api.receiving'

const containers = ref<ContainerRow[]>([])
const terminals = ref<TerminalOption[]>([])
const selectedContainer = ref<ContainerRow | null>(null)

const searchInput = ref('')
const search = ref('')
const terminal = ref('')
const status = ref('')
const containerType = ref('')

const start = ref(0)
const pageLength = 50
const hasMore = ref(false)

const loading = ref(false)
const loadingTerminals = ref(false)
const error = ref('')
const terminalError = ref('')

let searchTimer: ReturnType<typeof setTimeout> | undefined

const currentPage = computed(() => Math.floor(start.value / pageLength) + 1)

const statusOptions = [
  'Expected',
  'In Yard',
  'In Transit',
  'Loaded',
  'Out-Gated',
  'On Hold',
]

const typeOptions = [
  'Dry',
  'Reefer',
  'Open Top',
  'Flat Rack',
  'Tank',
  'Other',
]

async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${API}.${path}`, {
    credentials: 'same-origin',
  })

  const payload = await response.json().catch(() => ({}))

  if (!response.ok || payload.exc) {
    throw new Error(
      payload.message ||
      payload._error_message ||
      `Request failed (${response.status})`,
    )
  }

  return payload.message as T
}

async function loadTerminals() {
  loadingTerminals.value = true
  terminalError.value = ''

  try {
    terminals.value = await apiGet<TerminalOption[]>('get_receiving_terminals')
  } catch (err) {
    terminalError.value = err instanceof Error ? err.message : 'Could not load terminals.'
  } finally {
    loadingTerminals.value = false
  }
}

async function loadInventory() {
  loading.value = true
  error.value = ''

  const params = new URLSearchParams({
    start: String(start.value),
    page_length: String(pageLength),
  })

  if (search.value) params.set('search', search.value)
  if (terminal.value) params.set('terminal', terminal.value)
  if (status.value) params.set('operational_status', status.value)
  if (containerType.value) params.set('container_type', containerType.value)

  try {
    const response = await apiGet<InventoryResponse>(`get_container_inventory?${params.toString()}`)

    containers.value = response.data
    hasMore.value = response.has_more

    if (selectedContainer.value && !containers.value.some((item) => item.name === selectedContainer.value?.name)) {
      selectedContainer.value = null
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Could not load container inventory.'
    containers.value = []
    hasMore.value = false
  } finally {
    loading.value = false
  }
}

function applySearch() {
  search.value = searchInput.value.trim()
  start.value = 0
  selectedContainer.value = null
  void loadInventory()
}

function clearFilters() {
  searchInput.value = ''
  search.value = ''
  terminal.value = ''
  status.value = ''
  containerType.value = ''
  start.value = 0
  selectedContainer.value = null
  void loadInventory()
}

function changePage(direction: -1 | 1) {
  const nextStart = start.value + direction * pageLength

  if (nextStart < 0) return
  if (direction === 1 && !hasMore.value) return

  start.value = nextStart
  selectedContainer.value = null
  void loadInventory()
}

function statusTheme(status: string): 'gray' | 'red' | 'blue' | 'green' | 'amber' | 'violet' {
  switch (status) {
    case 'In Yard':
      return 'green'
    case 'Expected':
      return 'blue'
    case 'Out-Gated':
      return 'gray'
    case 'Damaged':
      return 'red'
    case 'On Hold':
      return 'amber'
    default:
      return 'violet'
  }
}

function terminalLabel(name?: string) {
  if (!name) return '—'

  const found = terminals.value.find((item) => item.name === name)
  return found ? `${found.terminal_name} (${found.terminal_code})` : name
}

function formatDate(value?: string) {
  if (!value) return '—'

  const date = new Date(value.replace(' ', 'T'))
  if (Number.isNaN(date.getTime())) return value

  return new Intl.DateTimeFormat(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(date)
}

watch([terminal, status, containerType], () => {
  start.value = 0
  selectedContainer.value = null
  void loadInventory()
})

onMounted(() => {
  void loadTerminals()
  void loadInventory()
})
</script>

<template>
  <div class="min-h-full bg-surface-gray-1">
    <div class="mx-auto max-w-[1500px] space-y-5 px-4 py-6 sm:px-6">
      <header class="flex flex-wrap items-start justify-between gap-4">
        <div>
          <p class="text-sm text-ink-gray-5">Yard Operations / Inventory</p>
          <h1 class="mt-1 text-2xl font-semibold text-ink-gray-9">
            Container Inventory
          </h1>
          <p class="mt-2 max-w-2xl text-sm text-ink-gray-6">
            Search and inspect container records, operational status, and
            recorded yard locations.
          </p>
        </div>

        <Button
          label="Receive container"
          icon-left="lucide-plus"
          route="/receiving"
        />
        <Button
          route="/relocation"
          label="Relocate container"
        />
      </header>

      <div
        v-if="error"
        role="alert"
        class="rounded-lg border border-outline-red-1 bg-surface-red-1 px-4 py-3 text-sm text-ink-red-3"
      >
        {{ error }}
        <Button
          class="ml-2"
          label="Retry"
          size="sm"
          @click="loadInventory"
        />
      </div>

      <div
        v-if="terminalError"
        class="rounded-lg border border-outline-orange-1 bg-surface-orange-1 px-4 py-3 text-sm text-ink-orange-3"
      >
        Terminal filter unavailable: {{ terminalError }}
      </div>

      <section class="rounded-xl border border-outline-gray-2 bg-surface-white">
        <div class="border-b border-outline-gray-1 p-4 sm:p-5">
          <form
            class="flex flex-col gap-3 lg:flex-row"
            @submit.prevent="applySearch"
          >
            <div class="relative min-w-0 flex-1">
              <span
                class="lucide-search pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-ink-gray-5"
              />
              <input
                v-model="searchInput"
                type="search"
                placeholder="Search container number or record ID"
                class="w-full rounded-lg border border-outline-gray-2 bg-surface-white py-2.5 pl-9 pr-3 text-sm text-ink-gray-8 outline-none focus:border-outline-gray-4"
              />
            </div>

            <Button
              type="submit"
              label="Search"
              icon-left="lucide-search"
              :loading="loading"
            />
          </form>

          <div class="mt-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            <div class="space-y-1">
              <label for="filter-terminal" class="text-xs font-medium text-ink-gray-6">
                Terminal
              </label>
              <select id="filter-terminal" v-model="terminal" class="filter-field">
                <option value="">All terminals</option>
                <option
                  v-for="item in terminals"
                  :key="item.name"
                  :value="item.name"
                >
                  {{ item.terminal_name }} ({{ item.terminal_code }})
                </option>
              </select>
            </div>

            <div class="space-y-1">
              <label for="filter-status" class="text-xs font-medium text-ink-gray-6">
                Operational status
              </label>
              <select id="filter-status" v-model="status" class="filter-field">
                <option value="">All statuses</option>
                <option v-for="item in statusOptions" :key="item" :value="item">
                  {{ item }}
                </option>
              </select>
            </div>

            <div class="space-y-1">
              <label for="filter-type" class="text-xs font-medium text-ink-gray-6">
                Container type
              </label>
              <select id="filter-type" v-model="containerType" class="filter-field">
                <option value="">All types</option>
                <option v-for="item in typeOptions" :key="item" :value="item">{{ item }}</option>
              </select>
            </div>

            <div class="flex items-end">
              <Button
                label="Clear filters"
                icon-left="lucide-rotate-ccw"
                variant="subtle"
                @click="clearFilters"
              />
            </div>
          </div>
        </div>

        <div class="flex flex-wrap items-center justify-between gap-2 px-4 py-3 sm:px-5">
          <div class="text-sm text-ink-gray-6">
            <span v-if="loading">Loading inventory…</span>
            <span v-else>
              {{ containers.length }} record{{ containers.length === 1 ? '' : 's' }}
              on this page
            </span>
          </div>

          <div class="flex items-center gap-2">
            <Button
              icon="lucide-chevron-left"
              aria-label="Previous page"
              :disabled="loading || start === 0"
              @click="changePage(-1)"
            />
            <span class="text-sm text-ink-gray-6">
              Page {{ currentPage }}
            </span>
            <Button
              icon="lucide-chevron-right"
              aria-label="Next page"
              :disabled="loading || !hasMore"
              @click="changePage(1)"
            />
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full min-w-[1050px] border-collapse text-left">
            <thead class="bg-surface-gray-1">
              <tr class="border-y border-outline-gray-1">
                <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                  Container
                </th>
                <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                  Type / Size
                </th>
                <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                  Shipping line
                </th>
                <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                  Status
                </th>
                <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                  Terminal
                </th>
                <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                  Yard slot
                </th>
                <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                  Last updated
                </th>
                <th class="px-4 py-3 text-xs font-semibold uppercase tracking-wide text-ink-gray-5">
                  Details
                </th>
              </tr>
            </thead>

            <tbody class="divide-y divide-outline-gray-1">
              <tr v-if="!loading && !containers.length">
                <td colspan="8" class="px-4 py-14 text-center">
                  <span class="lucide-container mx-auto mb-3 block size-8 text-ink-gray-4" />
                  <p class="font-medium text-ink-gray-8">
                    No containers found
                  </p>
                  <p class="mt-1 text-sm text-ink-gray-5">
                    Try changing your search or filters, or receive a container.
                  </p>
                  <Button
                    class="mt-4"
                    label="Receive container"
                    route="/receiving"
                  />
                </td>
              </tr>

              <tr
                v-for="item in containers"
                :key="item.name"
                class="transition-colors hover:bg-surface-gray-1"
                :class="selectedContainer?.name === item.name ? 'bg-surface-blue-1' : ''"
              >
                <td class="px-4 py-3">
                  <button
                    class="text-left"
                    @click="selectedContainer = item"
                  >
                    <span class="block font-semibold text-ink-gray-9">
                      {{ item.container_number }}
                    </span>
                    <span class="mt-0.5 block text-xs text-ink-gray-5">
                      {{ item.name }}
                    </span>
                  </button>
                </td>
                <td class="px-4 py-3">
                  <p class="text-sm text-ink-gray-8">
                    {{ item.container_type || '—' }}
                  </p>
                  <p class="mt-0.5 text-xs text-ink-gray-5">
                    {{ item.length_ft ? `${item.length_ft} ft` : '—' }}
                    <span v-if="item.iso_size_type">
                      · {{ item.iso_size_type }}
                    </span>
                  </p>
                </td>
                <td class="px-4 py-3 text-sm text-ink-gray-7">
                  {{ item.shipping_line || '—' }}
                </td>
                <td class="px-4 py-3">
                  <Badge
                    :theme="statusTheme(item.operational_status)"
                    :label="item.operational_status || 'Not set'"
                  />
                </td>
                <td class="px-4 py-3 text-sm text-ink-gray-7">
                  {{ terminalLabel(item.current_terminal) }}
                </td>
                <td class="px-4 py-3 text-sm text-ink-gray-7">
                  {{ item.current_yard_slot || '—' }}
                </td>
                <td class="px-4 py-3 text-sm text-ink-gray-6">
                  {{ formatDate(item.modified) }}
                </td>
                <td class="px-4 py-3">
                  <Button
                    label="View"
                    size="sm"
                    variant="subtle"
                    @click="selectedContainer = item"
                  />
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <div class="flex items-center justify-between border-t border-outline-gray-1 px-4 py-3 sm:px-5">
          <span class="text-xs text-ink-gray-5">
            Showing up to {{ pageLength }} records per page
          </span>
          <div class="flex items-center gap-2">
            <Button
              label="Previous"
              size="sm"
              :disabled="loading || start === 0"
              @click="changePage(-1)"
            />
            <Button
              label="Next"
              size="sm"
              :disabled="loading || !hasMore"
              @click="changePage(1)"
            />
          </div>
        </div>
      </section>

      <section
        v-if="selectedContainer"
        class="rounded-xl border border-outline-gray-2 bg-surface-white"
      >
        <div class="flex flex-wrap items-start justify-between gap-3 border-b border-outline-gray-1 px-5 py-4">
          <div>
            <p class="text-xs text-ink-gray-5">Container details</p>
            <h2 class="mt-1 text-lg font-semibold text-ink-gray-9">
              {{ selectedContainer.container_number }}
            </h2>
            <p class="mt-1 text-sm text-ink-gray-5">
              Record ID: {{ selectedContainer.name }}
            </p>
          </div>
          <div class="flex items-center gap-2">
            <Badge
              :theme="statusTheme(selectedContainer.operational_status)"
              :label="selectedContainer.operational_status || 'Not set'"
            />
            <Button
              icon="lucide-x"
              aria-label="Close container details"
              variant="subtle"
              @click="selectedContainer = null"
            />
          </div>
        </div>

        <div class="grid gap-5 p-5 sm:grid-cols-2 lg:grid-cols-3">
          <div>
            <p class="text-xs text-ink-gray-5">Container type</p>
            <p class="mt-1 text-sm font-medium text-ink-gray-8">
              {{ selectedContainer.container_type || '—' }}
            </p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">Length</p>
            <p class="mt-1 text-sm font-medium text-ink-gray-8">
              {{ selectedContainer.length_ft || '—' }}
              {{ selectedContainer.length_ft ? 'ft' : '' }}
            </p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">ISO size/type</p>
            <p class="mt-1 text-sm font-medium text-ink-gray-8">
              {{ selectedContainer.iso_size_type || '—' }}
            </p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">Shipping line</p>
            <p class="mt-1 text-sm font-medium text-ink-gray-8">
              {{ selectedContainer.shipping_line || '—' }}
            </p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">Current terminal</p>
            <p class="mt-1 text-sm font-medium text-ink-gray-8">
              {{ terminalLabel(selectedContainer.current_terminal) }}
            </p>
          </div>
          <div>
            <p class="text-xs text-ink-gray-5">Current yard slot</p>
            <p class="mt-1 text-sm font-medium text-ink-gray-8">
              {{ selectedContainer.current_yard_slot || 'Not currently assigned' }}
            </p>
          </div>
          <div class="sm:col-span-2 lg:col-span-3">
            <p class="text-xs text-ink-gray-5">Last updated</p>
            <p class="mt-1 text-sm font-medium text-ink-gray-8">
              {{ formatDate(selectedContainer.modified) }}
            </p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.filter-field {
  width: 100%;
  border: 1px solid var(--outline-gray-2);
  border-radius: 0.5rem;
  background: var(--surface-white);
  padding: 0.625rem 0.75rem;
  font-size: 0.875rem;
  color: var(--ink-gray-8);
  outline: none;
}

.filter-field:focus {
  border-color: var(--outline-gray-4);
}
</style>
