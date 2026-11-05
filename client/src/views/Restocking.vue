<template>
  <div class="restocking">
    <div class="page-header">
      <h2>{{ t('restocking.title') }}</h2>
      <p>{{ t('restocking.description') }}</p>
    </div>

    <div v-if="loading" class="loading">{{ t('common.loading') }}</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div class="card budget-card">
        <div class="budget-top">
          <div>
            <label class="stat-label" for="budget-slider">{{ t('restocking.budget') }}</label>
            <div class="budget-value">{{ money(budget) }}</div>
            <div class="budget-hint">{{ t('restocking.budgetHint') }}</div>
          </div>
        </div>
        <input
          id="budget-slider"
          v-model.number="budget"
          class="budget-slider"
          type="range"
          min="0"
          :max="budgetMax"
          :step="BUDGET_STEP"
          :style="{ '--fill': budgetFillPercent + '%' }"
          :disabled="budgetMax === 0"
        />
        <div class="budget-scale">
          <span>{{ money(0) }}</span>
          <span>{{ money(budgetMax) }}</span>
        </div>
      </div>

      <div class="stats-grid">
        <div class="stat-card info">
          <div class="stat-label">{{ t('restocking.recommendedTotal') }}</div>
          <div class="stat-value">{{ money(plan.total_cost) }}</div>
        </div>
        <div class="stat-card success">
          <div class="stat-label">{{ t('restocking.remaining') }}</div>
          <div class="stat-value">{{ money(plan.remaining_budget) }}</div>
        </div>
        <div class="stat-card">
          <div class="stat-label">{{ t('restocking.coverage') }}</div>
          <div class="stat-value">{{ coveragePercent }}%</div>
          <div class="stat-sub">{{ t('restocking.coverageHint', { total: money(plan.total_needed_cost) }) }}</div>
        </div>
      </div>

      <div v-if="placedOrder" class="order-success" role="status">
        <span>{{ t('restocking.orderPlaced', { number: placedOrder.order_number, days: placedOrder.lead_time_days }) }}</span>
        <router-link to="/orders" class="success-link">{{ t('restocking.viewInOrders') }}</router-link>
      </div>
      <div v-if="orderError" class="error">{{ orderError }}</div>

      <div class="card">
        <div class="card-header">
          <h3 class="card-title">{{ t('restocking.recommendations') }} ({{ plan.recommendations.length }})</h3>
          <button
            class="place-order-btn"
            :disabled="!canPlaceOrder"
            @click="placeOrder"
          >
            {{ placing ? t('restocking.placing') : t('restocking.placeOrder') }}
          </button>
        </div>
        <p class="priority-note">{{ t('restocking.priorityNote') }}</p>

        <div v-if="plan.total_needed_cost === 0" class="empty-state">{{ t('restocking.nothingNeeded') }}</div>
        <div v-else-if="plan.recommendations.length === 0" class="empty-state">{{ t('restocking.noRecommendations') }}</div>
        <div v-else class="table-container" :class="{ refreshing }">
          <table>
            <thead>
              <tr>
                <th>{{ t('restocking.table.sku') }}</th>
                <th>{{ t('restocking.table.itemName') }}</th>
                <th>{{ t('restocking.table.trend') }}</th>
                <th class="num">{{ t('restocking.table.forecast') }}</th>
                <th class="num">{{ t('restocking.table.onHand') }}</th>
                <th class="num">{{ t('restocking.table.needed') }}</th>
                <th class="num">{{ t('restocking.table.orderQty') }}</th>
                <th class="num">{{ t('restocking.table.unitCost') }}</th>
                <th class="num">{{ t('restocking.table.lineTotal') }}</th>
                <th class="num">{{ t('restocking.table.leadTime') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="rec in plan.recommendations" :key="rec.item_sku">
                <td><strong>{{ rec.item_sku }}</strong></td>
                <td>{{ translateProductName(rec.item_name) }}</td>
                <td>
                  <span :class="['badge', rec.trend]">{{ t(`trends.${rec.trend}`) }}</span>
                </td>
                <td class="num">{{ rec.forecasted_demand.toLocaleString() }}</td>
                <td class="num">{{ rec.quantity_on_hand.toLocaleString() }}</td>
                <td class="num">{{ rec.quantity_needed.toLocaleString() }}</td>
                <td class="num">
                  <strong>{{ rec.recommended_quantity.toLocaleString() }}</strong>
                  <span v-if="rec.recommended_quantity < rec.quantity_needed" class="badge warning partial">
                    {{ t('restocking.partial') }}
                  </span>
                </td>
                <td class="num">{{ money(rec.unit_cost, 2) }}</td>
                <td class="num"><strong>{{ money(rec.line_total) }}</strong></td>
                <td class="num">{{ t('orders.submitted.leadTimeDays', { days: rec.lead_time_days }) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted, onBeforeUnmount } from 'vue'
import { api } from '../api'
import { useI18n } from '../composables/useI18n'
import { formatCurrencyWithDecimals } from '../utils/currency'

const BUDGET_STEP = 500
const DEBOUNCE_MS = 200

export default {
  name: 'Restocking',
  setup() {
    const { t, currentCurrency, translateProductName } = useI18n()

    const loading = ref(true)
    const error = ref(null)
    const refreshing = ref(false)
    const placing = ref(false)
    const orderError = ref(null)
    const placedOrder = ref(null)

    // Budget is kept in USD; display converts to the active currency
    const budget = ref(0)
    const budgetMax = ref(0)
    const plan = ref({ budget: 0, total_cost: 0, remaining_budget: 0, total_needed_cost: 0, recommendations: [] })

    const money = (amount, decimals = 0) => formatCurrencyWithDecimals(amount, currentCurrency.value, decimals)

    const budgetFillPercent = computed(() => {
      return budgetMax.value ? (budget.value / budgetMax.value) * 100 : 0
    })

    const coveragePercent = computed(() => {
      if (!plan.value.total_needed_cost) return 100
      return Math.round((plan.value.total_cost / plan.value.total_needed_cost) * 100)
    })

    const canPlaceOrder = computed(() => {
      return !placing.value && !refreshing.value && plan.value.recommendations.length > 0
    })

    // Ignore responses that arrive after a newer request was sent
    let requestId = 0
    const fetchPlan = async (amount) => {
      const id = ++requestId
      const result = await api.getRestockRecommendations(amount)
      if (id === requestId) plan.value = result
      return result
    }

    const loadInitial = async () => {
      try {
        loading.value = true
        error.value = null
        const { total_needed_cost } = await fetchPlan(0)
        budgetMax.value = Math.ceil(total_needed_cost / BUDGET_STEP) * BUDGET_STEP
        budget.value = Math.round(budgetMax.value / 2 / BUDGET_STEP) * BUDGET_STEP
        await fetchPlan(budget.value)
      } catch (err) {
        error.value = 'Failed to load restocking recommendations: ' + err.message
      } finally {
        loading.value = false
      }
    }

    let debounceTimer = null
    watch(budget, (amount) => {
      if (loading.value) return
      placedOrder.value = null
      orderError.value = null
      refreshing.value = true
      clearTimeout(debounceTimer)
      debounceTimer = setTimeout(async () => {
        try {
          await fetchPlan(amount)
        } catch (err) {
          orderError.value = 'Failed to update recommendations: ' + err.message
        } finally {
          refreshing.value = false
        }
      }, DEBOUNCE_MS)
    })

    const placeOrder = async () => {
      try {
        placing.value = true
        orderError.value = null
        placedOrder.value = await api.createRestockOrder({
          budget: plan.value.budget,
          items: plan.value.recommendations.map(rec => ({
            item_sku: rec.item_sku,
            quantity: rec.recommended_quantity
          }))
        })
      } catch (err) {
        const detail = err.response?.data?.detail
        orderError.value = `${t('restocking.orderFailed')}: ${typeof detail === 'string' ? detail : err.message}`
      } finally {
        placing.value = false
      }
    }

    onMounted(loadInitial)
    onBeforeUnmount(() => clearTimeout(debounceTimer))

    return {
      t,
      BUDGET_STEP,
      loading,
      error,
      refreshing,
      placing,
      orderError,
      placedOrder,
      budget,
      budgetMax,
      plan,
      budgetFillPercent,
      coveragePercent,
      canPlaceOrder,
      money,
      placeOrder,
      translateProductName
    }
  }
}
</script>

<style scoped>
.budget-card {
  padding: 1.5rem;
}

.budget-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  margin-bottom: 1.25rem;
}

.budget-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: #0f172a;
  letter-spacing: -0.025em;
  line-height: 1.1;
}

.budget-hint {
  margin-top: 0.375rem;
  color: #64748b;
  font-size: 0.875rem;
}

.budget-slider {
  --fill: 0%;
  width: 100%;
  height: 8px;
  appearance: none;
  -webkit-appearance: none;
  border-radius: 999px;
  background: linear-gradient(to right, #2563eb var(--fill), #e2e8f0 var(--fill));
  outline: none;
  cursor: pointer;
}

.budget-slider:disabled {
  cursor: not-allowed;
  opacity: 0.5;
}

.budget-slider::-webkit-slider-thumb {
  -webkit-appearance: none;
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid #2563eb;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.2);
}

.budget-slider::-moz-range-thumb {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  background: #ffffff;
  border: 2px solid #2563eb;
  box-shadow: 0 1px 4px rgba(15, 23, 42, 0.2);
}

.budget-slider:focus-visible::-webkit-slider-thumb {
  box-shadow: 0 0 0 4px #bfdbfe;
}

.budget-scale {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
  color: #64748b;
  font-size: 0.813rem;
}

.stat-sub {
  margin-top: 0.25rem;
  color: #64748b;
  font-size: 0.813rem;
}

.priority-note {
  color: #64748b;
  font-size: 0.813rem;
  margin: -0.25rem 0 0.875rem;
}

.place-order-btn {
  background: #2563eb;
  color: #ffffff;
  border: none;
  border-radius: 6px;
  padding: 0.625rem 1.25rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.15s ease;
}

.place-order-btn:hover:not(:disabled) {
  background: #1d4ed8;
}

.place-order-btn:disabled {
  background: #94a3b8;
  cursor: not-allowed;
}

.order-success {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  background: #ecfdf5;
  border: 1px solid #a7f3d0;
  color: #065f46;
  padding: 0.875rem 1rem;
  border-radius: 8px;
  margin-bottom: 1.25rem;
  font-size: 0.938rem;
}

.success-link {
  color: #047857;
  font-weight: 600;
  white-space: nowrap;
}

.empty-state {
  padding: 2rem;
  text-align: center;
  color: #64748b;
  font-size: 0.938rem;
}

.table-container {
  transition: opacity 0.15s ease;
}

.table-container.refreshing {
  opacity: 0.55;
}

.num {
  text-align: right;
  white-space: nowrap;
}

.partial {
  margin-left: 0.5rem;
  padding: 0.125rem 0.5rem;
  font-size: 0.688rem;
}
</style>
