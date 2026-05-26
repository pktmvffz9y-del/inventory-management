<template>
  <div class="restocking">
    <div class="page-header">
      <h2>Restocking</h2>
      <p>Budget-based restocking recommendations from demand forecasts.</p>
    </div>

    <div v-if="loading" class="loading">Loading...</div>
    <div v-else-if="error" class="error">{{ error }}</div>
    <div v-else>
      <div v-if="orderPlaced" class="success-banner">
        <h3>Order Placed Successfully</h3>
        <p>Order {{ placedOrder.order_number }} has been submitted. Expected delivery: {{ formatDate(placedOrder.expected_delivery) }}</p>
        <button class="btn-secondary" @click="resetOrderState">Place Another Order</button>
      </div>

      <template v-else>
        <!-- Budget slider section -->
        <div class="card budget-card">
          <div class="card-header">
            <h3 class="card-title">Available Budget</h3>
          </div>
          <div class="budget-control">
            <input type="range" min="5000" max="200000" step="1000" v-model.number="budget" />
            <div class="budget-display">${{ budget.toLocaleString('en-US') }}</div>
          </div>
        </div>

        <!-- Summary bar -->
        <div class="summary-bar" :class="{ 'over-budget': overBudget }">
          <span>{{ selectedItems.length }} items selected</span>
          <span class="budget-usage">
            ${{ totalSelected.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}
            of ${{ budget.toLocaleString('en-US') }} budget used
          </span>
          <button class="btn-primary" @click="placeOrder" :disabled="selectedItems.length === 0 || submitting">
            {{ submitting ? 'Placing Order...' : 'Place Order' }}
          </button>
        </div>

        <!-- Recommendations table -->
        <div class="card">
          <div class="card-header">
            <h3 class="card-title">Recommendations ({{ recommendations.length }})</h3>
          </div>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th style="width:40px"></th>
                  <th>Item</th>
                  <th>SKU</th>
                  <th>Trend</th>
                  <th>On Hand</th>
                  <th>To Order</th>
                  <th>Unit Cost</th>
                  <th>Total Cost</th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="item in recommendations"
                  :key="item.item_sku"
                  :class="{ 'outside-budget': !withinBudgetSkus.has(item.item_sku) && !checkedSkus.has(item.item_sku) }"
                >
                  <td>
                    <input type="checkbox" :checked="checkedSkus.has(item.item_sku)" @change="toggleItem(item.item_sku)" />
                  </td>
                  <td>{{ item.item_name }}</td>
                  <td class="sku-cell">{{ item.item_sku }}</td>
                  <td><span :class="['badge', trendBadgeClass(item.trend)]">{{ item.trend }}</span></td>
                  <td>{{ item.quantity_on_hand.toLocaleString('en-US') }}</td>
                  <td>{{ item.quantity_to_order.toLocaleString('en-US') }}</td>
                  <td>${{ item.unit_cost.toFixed(2) }}</td>
                  <td>${{ item.total_cost.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 }) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </template>
    </div>
  </div>
</template>

<script>
import { ref, computed, watch, onMounted } from 'vue'
import { api } from '../api'

export default {
  name: 'Restocking',
  setup() {
    const recommendations = ref([])
    const budget = ref(50000)
    // checkedSkus is a Set; always assign a new Set to trigger reactivity
    const checkedSkus = ref(new Set())
    const loading = ref(false)
    const error = ref(null)
    const orderPlaced = ref(false)
    const placedOrder = ref(null)
    const submitting = ref(false)

    // Greedy allocation: iterate recommendations sorted by priority desc,
    // include each item if its total_cost fits within the remaining budget.
    // The API already returns items sorted by priority descending.
    const withinBudgetSkus = computed(() => {
      let runningTotal = 0
      const result = new Set()
      for (const item of recommendations.value) {
        if (runningTotal + item.total_cost <= budget.value) {
          result.add(item.item_sku)
          runningTotal += item.total_cost
        }
      }
      return result
    })

    // When budget changes, reset checkedSkus to match the new greedy allocation
    watch(withinBudgetSkus, (newSkus) => {
      checkedSkus.value = new Set(newSkus)
    }, { immediate: false })

    const selectedItems = computed(() => {
      return recommendations.value.filter(item => checkedSkus.value.has(item.item_sku))
    })

    const totalSelected = computed(() => {
      return selectedItems.value.reduce((sum, item) => sum + item.total_cost, 0)
    })

    const overBudget = computed(() => totalSelected.value > budget.value)

    const trendBadgeClass = (trend) => {
      const map = {
        increasing: 'success',
        stable: 'info',
        decreasing: 'danger'
      }
      return map[trend] || 'info'
    }

    // Toggle a single SKU in checkedSkus by replacing the Set
    const toggleItem = (sku) => {
      const next = new Set(checkedSkus.value)
      if (next.has(sku)) {
        next.delete(sku)
      } else {
        next.add(sku)
      }
      checkedSkus.value = next
    }

    const formatDate = (dateString) => {
      return new Date(dateString).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
      })
    }

    const placeOrder = async () => {
      const items = selectedItems.value.map(i => ({
        sku: i.item_sku,
        name: i.item_name,
        quantity: i.quantity_to_order,
        unit_price: i.unit_cost
      }))
      submitting.value = true
      try {
        const order = await api.createRestockingOrder(items)
        placedOrder.value = order
        orderPlaced.value = true
        checkedSkus.value = new Set()
      } catch (err) {
        error.value = 'Failed to place order: ' + err.message
      } finally {
        submitting.value = false
      }
    }

    const resetOrderState = () => {
      orderPlaced.value = false
      placedOrder.value = null
      // Re-sync checkedSkus to current budget allocation
      checkedSkus.value = new Set(withinBudgetSkus.value)
    }

    const loadRecommendations = async () => {
      loading.value = true
      error.value = null
      try {
        recommendations.value = await api.getRestockingRecommendations()
        // Initialize checkedSkus after data loads so withinBudgetSkus is populated
        checkedSkus.value = new Set(withinBudgetSkus.value)
      } catch (err) {
        error.value = 'Failed to load recommendations: ' + err.message
        console.error(err)
      } finally {
        loading.value = false
      }
    }

    onMounted(() => loadRecommendations())

    return {
      recommendations,
      budget,
      checkedSkus,
      loading,
      error,
      orderPlaced,
      placedOrder,
      submitting,
      withinBudgetSkus,
      selectedItems,
      totalSelected,
      overBudget,
      trendBadgeClass,
      toggleItem,
      formatDate,
      placeOrder,
      resetOrderState
    }
  }
}
</script>

<style scoped>
.budget-card { margin-bottom: 1rem; }

.budget-control {
  display: flex;
  align-items: center;
  gap: 1.5rem;
  padding: 1rem 0;
}

.budget-control input[type="range"] {
  flex: 1;
  accent-color: #3b82f6;
}

.budget-display {
  font-size: 1.5rem;
  font-weight: 700;
  color: #0f172a;
  min-width: 120px;
}

.summary-bar {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.875rem 1.25rem;
  margin-bottom: 1rem;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
}

.summary-bar.over-budget {
  background: #fef2f2;
  border-color: #fca5a5;
}

.budget-usage {
  flex: 1;
  color: #64748b;
}

.summary-bar.over-budget .budget-usage {
  color: #ef4444;
  font-weight: 600;
}

.btn-primary {
  background: #3b82f6;
  color: white;
  border: none;
  padding: 0.5rem 1.25rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.btn-primary:not(:disabled):hover {
  background: #2563eb;
}

.btn-secondary {
  background: white;
  color: #3b82f6;
  border: 1px solid #3b82f6;
  padding: 0.5rem 1.25rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 500;
}

.btn-secondary:hover {
  background: #eff6ff;
}

.outside-budget td {
  color: #94a3b8;
}

.sku-cell {
  font-family: monospace;
  font-size: 0.875rem;
  color: #64748b;
}

.success-banner {
  background: #f0fdf4;
  border: 1px solid #86efac;
  border-radius: 8px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  text-align: center;
}

.success-banner h3 {
  color: #166534;
  margin-bottom: 0.5rem;
}

.success-banner p {
  color: #15803d;
  margin-bottom: 1rem;
}
</style>
