<template>
  <div class="orders">
    <div class="page-header">
      <h2>{{ t('orders.title') }}</h2>
      <p>{{ t('orders.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="stats-grid">
        <div class="stat-card success">
          <div class="stat-label">{{ t('status.delivered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Delivered').length }}</div>
        </div>
        <div class="stat-card info">
          <div class="stat-label">{{ t('status.shipped') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Shipped').length }}</div>
        </div>
        <div class="stat-card warning">
          <div class="stat-label">{{ t('status.processing') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Processing').length }}</div>
        </div>
        <div class="stat-card danger">
          <div class="stat-label">{{ t('status.backordered') }}</div>
          <div class="stat-value">{{ getOrdersByStatus('Backordered').length }}</div>
        </div>
      </div>

      <div class="card submitted-card">
        <div class="card-header submitted-header">
          <h3 class="card-title">{{ t('orders.submitted.title') }} ({{ submittedOrders.length }})</h3>
          <p class="submitted-description">{{ t('orders.submitted.description') }}</p>
        </div>
        <div v-if="submittedError" class="submitted-error">{{ submittedError }}</div>
        <div v-else-if="submittedOrders.length === 0" class="submitted-empty">
          {{ t('orders.submitted.empty') }}
        </div>
        <div v-else class="table-container">
          <table class="orders-table">
            <thead>
              <tr>
                <th class="col-order-number">{{ t('orders.table.orderNumber') }}</th>
                <th class="col-datetime">{{ t('orders.submitted.submittedAt') }}</th>
                <th class="col-items">{{ t('orders.table.items') }}</th>
                <th class="col-lead">{{ t('orders.submitted.leadTime') }}</th>
                <th class="col-date">{{ t('orders.table.expectedDelivery') }}</th>
                <th class="col-status">{{ t('orders.table.status') }}</th>
                <th class="col-value">{{ t('orders.submitted.totalCost') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in submittedOrders" :key="order.id">
                <td class="col-order-number"><strong>{{ order.order_number }}</strong></td>
                <td class="col-datetime">{{ formatDateTime(order.submitted_at) }}</td>
                <td class="col-items">
                  <details class="items-details">
                    <summary class="items-summary">
                      {{ t('orders.itemsCount', { count: order.items.length }) }}
                    </summary>
                    <div class="items-dropdown">
                      <div v-for="item in order.items" :key="item.item_sku" class="item-entry">
                        <span class="item-name">{{ item.item_name }}</span>
                        <span class="item-meta">{{ t('orders.quantity') }}: {{ item.quantity }} @ {{ formatCost(item.unit_cost, 2) }}</span>
                      </div>
                    </div>
                  </details>
                </td>
                <td class="col-lead">
                  <span class="lead-time">{{ t('orders.submitted.leadTimeDays', { days: order.lead_time_days }) }}</span>
                </td>
                <td class="col-date">{{ formatDate(order.expected_delivery) }}</td>
                <td class="col-status">
                  <span class="badge info">{{ t(`status.${order.status.toLowerCase()}`) }}</span>
                </td>
                <td class="col-value"><strong>{{ formatCost(order.total_cost, 2) }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('orders.allOrders') }} ({{ orders.length }})</h3>
        </div>
        <div class="table-container">
          <table class="orders-table">
            <thead>
              <tr>
                <th class="col-order-number">{{ t('orders.table.orderNumber') }}</th>
                <th class="col-customer">{{ t('orders.table.customer') }}</th>
                <th class="col-items">{{ t('orders.table.items') }}</th>
                <th class="col-status">{{ t('orders.table.status') }}</th>
                <th class="col-date">{{ t('orders.table.orderDate') }}</th>
                <th class="col-date">{{ t('orders.table.expectedDelivery') }}</th>
                <th class="col-value">{{ t('orders.table.totalValue') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="order in orders" :key="order.id">
                <td class="col-order-number"><strong>{{ order.order_number }}</strong></td>
                <td class="col-customer">{{ translateCustomerName(order.customer) }}</td>
                <td class="col-items">
                  <details class="items-details">
                    <summary class="items-summary">
                      {{ t('orders.itemsCount', { count: order.items.length }) }}
                    </summary>
                    <div class="items-dropdown">
                      <div v-for="(item, idx) in order.items" :key="idx" class="item-entry">
                        <span class="item-name">{{ translateProductName(item.name) }}</span>
                        <span class="item-meta">{{ t('orders.quantity') }}: {{ item.quantity }} @ {{ currencySymbol }}{{ item.unit_price }}</span>
                      </div>
                    </div>
                  </details>
                </td>
                <td class="col-status">
                  <span :class="['badge', getOrderStatusClass(order.status)]">
                    {{ t(`status.${order.status.toLowerCase()}`) }}
                  </span>
                </td>
                <td class="col-date">{{ formatDate(order.order_date) }}</td>
                <td class="col-date">{{ formatDate(order.expected_delivery) }}</td>
                <td class="col-value"><strong>{{ currencySymbol }}{{ order.total_value.toLocaleString() }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, watch, computed } from 'vue'
import { api } from '../api'
import { useFilters } from '../composables/useFilters'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

export default {
  name: 'Orders',
  setup() {
    const { t, currentCurrency, translateProductName, translateCustomerName } = useI18n()

    const currencySymbol = computed(() => {
      return currentCurrency.value === 'JPY' ? '¥' : '$'
    })
    const loading = ref(true)
    const error = ref(null)
    const orders = ref([])

    // Use shared filters
    const {
      selectedPeriod,
      selectedLocation,
      selectedCategory,
      selectedStatus,
      getCurrentFilters
    } = useFilters()

    const loadOrders = async () => {
      try {
        loading.value = true
        const filters = getCurrentFilters()
        const fetchedOrders = await api.getOrders(filters)

        // Sort orders by order_date (earliest first)
        orders.value = fetchedOrders.sort((a, b) => {
          const dateA = new Date(a.order_date)
          const dateB = new Date(b.order_date)
          return dateA - dateB
        })
      } catch (err) {
        error.value = 'Failed to load orders: ' + err.message
      } finally {
        loading.value = false
      }
    }

    // Watch for filter changes and reload data
    watch([selectedPeriod, selectedLocation, selectedCategory, selectedStatus], () => {
      loadOrders()
    })

    const getOrdersByStatus = (status) => {
      return orders.value.filter(order => order.status === status)
    }

    const getOrderStatusClass = (status) => {
      const statusMap = {
        'Delivered': 'success',
        'Shipped': 'info',
        'Processing': 'warning',
        'Backordered': 'danger'
      }
      return statusMap[status] || 'info'
    }

    const formatDate = (dateString) => {
      const { currentLocale } = useI18n()
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      const date = new Date(dateString)
      if (!dateString || isNaN(date.getTime())) return '—'
      return date.toLocaleDateString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const formatDateTime = (dateString) => {
      const { currentLocale } = useI18n()
      const locale = currentLocale.value === 'ja' ? 'ja-JP' : 'en-US'
      const date = new Date(dateString)
      if (!dateString || isNaN(date.getTime())) return '—'
      return date.toLocaleString(locale, {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
      })
    }

    const formatCost = (amount, decimals = 2) => {
      return formatCurrencyWithDecimals(Number(amount) || 0, currentCurrency.value, decimals)
    }

    // Submitted restocking orders (not affected by the global filters)
    const submittedOrders = ref([])
    const submittedError = ref(null)

    const loadSubmittedOrders = async () => {
      try {
        submittedError.value = null
        const result = await api.getRestockOrders()
        submittedOrders.value = Array.isArray(result) ? result : []
      } catch (err) {
        submittedError.value = 'Failed to load submitted orders: ' + err.message
      }
    }

    onMounted(() => {
      loadOrders()
      loadSubmittedOrders()
    })

    return {
      t,
      loading,
      error,
      orders,
      getOrdersByStatus,
      getOrderStatusClass,
      formatDate,
      formatDateTime,
      formatCost,
      submittedOrders,
      submittedError,
      currencySymbol,
      translateProductName,
      translateCustomerName
    }
  }
}
</script>

<style scoped>
/* Fixed table layout to prevent column shifting */
.orders-table {
  table-layout: fixed;
  width: 100%;
}

/* Column widths */
.col-order-number {
  width: 130px;
}

.col-customer {
  width: 180px;
}

.col-items {
  width: 200px;
}

.col-status {
  width: 130px;
}

.col-date {
  width: 140px;
}

.col-value {
  width: 120px;
}

/* Submitted orders */
.col-datetime {
  width: 170px;
}

.col-lead {
  width: 130px;
}

.submitted-card {
  margin-bottom: 1.5rem;
}

.submitted-header {
  display: block;
}

.submitted-description {
  margin: 0.25rem 0 0;
  font-size: 0.875rem;
  color: #64748b;
}

.submitted-empty {
  padding: 2rem 1rem;
  text-align: center;
  color: #64748b;
  font-size: 0.875rem;
}

.submitted-error {
  padding: 0.75rem 1rem;
  color: #b91c1c;
  font-size: 0.875rem;
}

.lead-time {
  display: inline-block;
  padding: 0.25rem 0.625rem;
  border-radius: 6px;
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  color: #0f172a;
  font-size: 0.938rem;
  font-weight: 700;
  white-space: nowrap;
}

/* Items details styling */
.items-details {
  position: relative;
}

.items-summary {
  cursor: pointer;
  color: #3b82f6;
  font-weight: 500;
  list-style: none;
  user-select: none;
  display: inline-block;
}

.items-summary::-webkit-details-marker {
  display: none;
}

.items-summary::before {
  content: '▶';
  display: inline-block;
  margin-right: 0.375rem;
  font-size: 0.75rem;
  transition: transform 0.2s;
}

.items-details[open] .items-summary::before {
  transform: rotate(90deg);
}

.items-summary:hover {
  color: #2563eb;
  text-decoration: underline;
}

/* Dropdown container */
.items-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  margin-top: 0.5rem;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);
  padding: 0.75rem;
  z-index: 10;
  min-width: 300px;
  max-width: 400px;
}

.item-entry {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.5rem;
  border-bottom: 1px solid #f1f5f9;
}

.item-entry:last-child {
  border-bottom: none;
}

.item-name {
  font-size: 0.875rem;
  font-weight: 500;
  color: #0f172a;
}

.item-meta {
  font-size: 0.813rem;
  color: #64748b;
}
</style>
