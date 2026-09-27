<template>
  <!-- Loading state -->
  <div
    v-if="list.loading && !list.data?.length"
    class="absolute top-0 z-10 flex h-full w-full items-center justify-center"
  >
    <LoadingIndicator :scale="8" />
  </div>

  <!-- List -->
  <ListView
    v-else-if="rows.length"
    class="flex-1"
    :columns="options.columns"
    :rows="rows"
    :row-key="options.rowKey || 'name'"
    :options="{
      selectable: options.selectable ?? true,
      showTooltip: false,
      resizeColumn: true,
      getRowRoute: options.getRowRoute || null,
      onRowClick: options.onRowClick || null,
      emptyState,
    }"
  >
    <ListHeader class="mx-3 sm:mx-5">
      <ListHeaderItem
        v-for="column in options.columns"
        :key="column.key"
        :item="column"
      />
    </ListHeader>
    <ListRows>
      <ListRow
        v-for="row in rows"
        :key="row[options.rowKey || 'name']"
        :row="row"
        class="mx-3 sm:mx-5"
        v-slot="{ column, item }"
      >
        <ListRowItem
          :column="column"
          :row="row"
          :item="item"
          :align="column.align"
        >
          <template #default="{ label }">
            <slot
              name="cell"
              :column="column"
              :item="item"
              :row="row"
              :label="label"
            >
              <div class="truncate text-base">{{ label }}</div>
            </slot>
          </template>
        </ListRowItem>
      </ListRow>
    </ListRows>
    <ListSelectBanner />
  </ListView>

  <!-- Empty state -->
  <EmptyState
    v-else-if="!list.loading"
    :title="emptyState.title"
    :description="emptyState.description"
    :icon="options.emptyStateIcon"
  />

  <!-- Footer -->
  <div
    v-if="rows.length"
    class="border-t border-outline-gray-1 px-3 py-2 sm:px-5"
  >
    <ListFooter
      v-model="pageLength"
      :options="{
        rowCount: rows.length,
        totalCount: totalCount.data || rows.length,
      }"
      @loadMore="list.next()"
    />
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import {
  ListView,
  ListHeader,
  ListHeaderItem,
  ListRows,
  ListRow,
  ListRowItem,
  ListSelectBanner,
  ListFooter,
  LoadingIndicator,
  createListResource,
  createResource,
} from 'frappe-ui'
import EmptyState from '@/components/EmptyState.vue'

const props = defineProps({
  options: {
    type: Object,
    required: true,
    // { doctype, columns, fields, filters, orderBy, rowKey, pageLength,
    //   selectable, getRowRoute, onRowClick, emptyState, emptyStateIcon }
  },
})

const pageLength = ref(props.options.pageLength || 20)

const emptyState = computed(
  () =>
    props.options.emptyState || {
      title: __('Sin registros'),
      description: __('No hay documentos para mostrar'),
    },
)

const list = createListResource({
  doctype: props.options.doctype,
  fields: props.options.fields || ['name'],
  filters: props.options.filters || {},
  orderBy: props.options.orderBy || 'modified desc',
  pageLength: pageLength.value,
  auto: true,
})

const totalCount = createResource({
  url: 'frappe.client.get_count',
  params: {
    doctype: props.options.doctype,
    filters: props.options.filters || {},
  },
  auto: true,
})

const rows = computed(() => list.data || [])

watch(pageLength, (value) => {
  list.pageLength = value
  list.reload()
})

defineExpose({ list, reload: () => list.reload() })
</script>
