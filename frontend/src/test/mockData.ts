import type { AskResponse, ChartSpecResponse } from '../types/api'

type Entry = {
  match: string | RegExp
  answer: string
  chart?: ChartSpecResponse
  sql?: { sql: string; explanation: string }
}

const ENTRIES: Entry[] = [
  {
    match: /^how many orders/i,
    answer: 'There are **12,458** orders in the database.',
    sql: { sql: 'SELECT COUNT(*) AS order_count FROM orders', explanation: 'Counting all orders.' },
  },
  {
    match: /^how many customers/i,
    answer: 'We have **9,940** unique customers.',
    sql: { sql: 'SELECT COUNT(DISTINCT customer_id) AS customer_count FROM customers', explanation: 'Counting unique customers.' },
  },
  {
    match: /^total revenue/i,
    answer: 'The total revenue across all orders is **$13,591,840.72**.',
    chart: {
      chart_type: 'bar',
      title: 'Monthly Revenue (Last 6 Months)',
      data: [
        { month: 'Jan', revenue: 2100000 },
        { month: 'Feb', revenue: 1950000 },
        { month: 'Mar', revenue: 2340000 },
        { month: 'Apr', revenue: 2210000 },
        { month: 'May', revenue: 2560000 },
        { month: 'Jun', revenue: 2431840 },
      ],
      x_key: 'month',
      y_key: 'revenue',
    },
    sql: { sql: 'SELECT SUM(payment_value) AS total_revenue FROM order_payments', explanation: 'Summing all payment values.' },
  },
  {
    match: /^average order value/i,
    answer: 'The average order value is **$137.88**.',
    chart: {
      chart_type: 'bar',
      title: 'Average Order Value by Month',
      data: [
        { month: 'Jan', avg: 132 },
        { month: 'Feb', avg: 128 },
        { month: 'Mar', avg: 141 },
        { month: 'Apr', avg: 135 },
        { month: 'May', avg: 145 },
        { month: 'Jun', avg: 137 },
      ],
      x_key: 'month',
      y_key: 'avg',
    },
    sql: { sql: 'SELECT AVG(payment_value) AS avg_order_value FROM order_payments', explanation: 'Calculating average payment per order.' },
  },
  {
    match: /^top.*products/i,
    answer: 'The top 5 products by sales volume are:\n1. **Bed Bath Table** — 1,112 units\n2. **Health & Beauty** — 987 units\n3. **Sports & Leisure** — 856 units\n4. **Furniture & Decor** — 789 units\n5. **Computers & Accessories** — 743 units',
    chart: {
      chart_type: 'bar',
      title: 'Top 5 Product Categories by Sales',
      data: [
        { category: 'Bed Bath Table', units: 1112 },
        { category: 'Health & Beauty', units: 987 },
        { category: 'Sports & Leisure', units: 856 },
        { category: 'Furniture & Decor', units: 789 },
        { category: 'Computers', units: 743 },
      ],
      x_key: 'category',
      y_key: 'units',
    },
    sql: { sql: 'SELECT p.product_category_name, COUNT(*) AS units FROM order_items oi JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY units DESC LIMIT 5', explanation: 'Aggregating sales by product category.' },
  },
  {
    match: /^top.*customers/i,
    answer: 'The top 5 customers by total spend are:\n1. **Customer #15983** — $12,874\n2. **Customer #20541** — $11,230\n3. **Customer #8712** — $9,847\n4. **Customer #44301** — $9,112\n5. **Customer #36789** — $8,995',
    sql: { sql: 'SELECT c.customer_unique_id, SUM(p.payment_value) AS total_spend FROM customers c JOIN orders o ON c.customer_id = o.customer_id JOIN order_payments p ON o.order_id = p.order_id GROUP BY c.customer_unique_id ORDER BY total_spend DESC LIMIT 5', explanation: 'Finding highest-spending customers.' },
  },
  {
    match: /^monthly.*trend/i,
    answer: 'Order volume has grown steadily over the last 6 months, from 1,450 orders in January to **1,890** in June — a **30% increase**.',
    chart: {
      chart_type: 'line',
      title: 'Monthly Order Trend',
      data: [
        { month: 'Jan', orders: 1450 },
        { month: 'Feb', orders: 1520 },
        { month: 'Mar', orders: 1610 },
        { month: 'Apr', orders: 1700 },
        { month: 'May', orders: 1780 },
        { month: 'Jun', orders: 1890 },
      ],
      x_key: 'month',
      y_key: 'orders',
    },
    sql: { sql: "SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month, COUNT(*) AS orders FROM orders GROUP BY month ORDER BY month DESC LIMIT 6", explanation: 'Aggregating orders by month.' },
  },
  {
    match: /^sales.*category/i,
    answer: 'Sales by category:\n- **Bed Bath Table**: $2.1M\n- **Health & Beauty**: $1.8M\n- **Sports & Leisure**: $1.6M\n- **Furniture & Decor**: $1.4M\n- **Computers**: $1.2M',
    chart: {
      chart_type: 'bar',
      title: 'Sales by Product Category',
      data: [
        { category: 'Bed Bath', revenue: 2100000 },
        { category: 'Health', revenue: 1800000 },
        { category: 'Sports', revenue: 1600000 },
        { category: 'Furniture', revenue: 1400000 },
        { category: 'Computers', revenue: 1200000 },
        { category: 'Others', revenue: 3491840 },
      ],
      x_key: 'category',
      y_key: 'revenue',
    },
    sql: { sql: 'SELECT p.product_category_name, SUM(py.payment_value) AS revenue FROM order_items oi JOIN products p ON oi.product_id = p.product_id JOIN order_payments py ON oi.order_id = py.order_id GROUP BY p.product_category_name ORDER BY revenue DESC', explanation: 'Revenue breakdown by product category.' },
  },
  {
    match: /^payment.*method|payment.*type|how.*pay/i,
    answer: 'Payment method breakdown:\n- **Credit Card**: 74.3%\n- **Boleto**: 18.2%\n- **Debit Card**: 4.5%\n- **Voucher**: 3.0%',
    chart: {
      chart_type: 'bar',
      title: 'Payment Methods',
      data: [
        { method: 'Credit Card', pct: 74.3 },
        { method: 'Boleto', pct: 18.2 },
        { method: 'Debit Card', pct: 4.5 },
        { method: 'Voucher', pct: 3.0 },
      ],
      x_key: 'method',
      y_key: 'pct',
    },
    sql: { sql: 'SELECT payment_type, COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS percentage FROM order_payments GROUP BY payment_type ORDER BY percentage DESC', explanation: 'Calculating payment method distribution.' },
  },
  {
    match: /^order.*status/i,
    answer: 'Current order status breakdown:\n- **Delivered**: 95.2%\n- **Shipped**: 2.1%\n- **Processing**: 1.4%\n- **Cancelled**: 0.9%\n- **Unavailable**: 0.4%',
    chart: {
      chart_type: 'bar',
      title: 'Order Status Distribution',
      data: [
        { status: 'Delivered', pct: 95.2 },
        { status: 'Shipped', pct: 2.1 },
        { status: 'Processing', pct: 1.4 },
        { status: 'Cancelled', pct: 0.9 },
        { status: 'Unavailable', pct: 0.4 },
      ],
      x_key: 'status',
      y_key: 'pct',
    },
    sql: { sql: 'SELECT order_status, COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS percentage FROM orders GROUP BY order_status ORDER BY percentage DESC', explanation: 'Status distribution of all orders.' },
  },
  {
    match: /^review.*score|rating|average.*review/i,
    answer: 'The average review score across all products is **4.1 / 5.0**.',
    chart: {
      chart_type: 'bar',
      title: 'Review Score Distribution',
      data: [
        { score: '1 star', count: 1250 },
        { score: '2 star', count: 980 },
        { score: '3 star', count: 2340 },
        { score: '4 star', count: 5670 },
        { score: '5 star', count: 12450 },
      ],
      x_key: 'score',
      y_key: 'count',
    },
    sql: { sql: 'SELECT review_score, COUNT(*) AS count FROM order_reviews GROUP BY review_score ORDER BY review_score', explanation: 'Distribution of review scores.' },
  },
  {
    match: /^delivery.*time|shipping.*time|how long.*deliver/i,
    answer: 'The average delivery time is **8.3 days** from purchase to delivery. 72% of orders arrive within the estimated delivery date.',
    sql: { sql: "SELECT AVG(delivery_days) AS avg_delivery, SUM(CASE WHEN delivery_days <= estimated_days THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS on_time_pct FROM (SELECT EXTRACT(DAY FROM order_delivered_customer_date - order_purchase_timestamp) AS delivery_days, EXTRACT(DAY FROM order_estimated_delivery_date - order_purchase_timestamp) AS estimated_days FROM orders WHERE order_status = 'delivered') sub", explanation: 'Calculating average delivery time and on-time rate.' },
  },
  {
    match: /^sellers|how many sellers/i,
    answer: 'There are **3,095** active sellers on the platform.',
    sql: { sql: 'SELECT COUNT(DISTINCT seller_id) AS seller_count FROM sellers', explanation: 'Counting unique sellers.' },
  },
  {
    match: /^geolocation|customers.*state|orders.*state|by region/i,
    answer: 'Orders by state:\n- **SP (São Paulo)**: 41,920 orders\n- **RJ (Rio de Janeiro)**: 13,520 orders\n- **MG (Minas Gerais)**: 11,340 orders\n- **RS (Rio Grande do Sul)**: 6,710 orders\n- **PR (Paraná)**: 5,980 orders',
    chart: {
      chart_type: 'bar',
      title: 'Orders by State',
      data: [
        { state: 'SP', orders: 41920 },
        { state: 'RJ', orders: 13520 },
        { state: 'MG', orders: 11340 },
        { state: 'RS', orders: 6710 },
        { state: 'PR', orders: 5980 },
        { state: 'Others', orders: 14990 },
      ],
      x_key: 'state',
      y_key: 'orders',
    },
    sql: { sql: 'SELECT c.customer_state, COUNT(*) AS orders FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_state ORDER BY orders DESC LIMIT 5', explanation: 'Geographic distribution of orders.' },
  },
  {
    match: /^weekend.*vs.*weekday|order.*day of week|orders.*weekend/i,
    answer: 'Weekend orders account for **22%** of total orders, while weekdays account for **78%**. Sunday is the slowest day.',
    chart: {
      chart_type: 'bar',
      title: 'Orders by Day of Week',
      data: [
        { day: 'Mon', orders: 2340 },
        { day: 'Tue', orders: 2450 },
        { day: 'Wed', orders: 2510 },
        { day: 'Thu', orders: 2480 },
        { day: 'Fri', orders: 2390 },
        { day: 'Sat', orders: 1820 },
        { day: 'Sun', orders: 1120 },
      ],
      x_key: 'day',
      y_key: 'orders',
    },
    sql: { sql: "SELECT TO_CHAR(order_purchase_timestamp, 'Day') AS day, COUNT(*) AS orders FROM orders GROUP BY day ORDER BY orders DESC", explanation: 'Analyzing order patterns by day of week.' },
  },
  {
    match: /^seasonal|order.*month|month.*order/i,
    answer: 'Order volume peaks in **November** (holiday season) and **March**, with the lowest volume in January.',
    chart: {
      chart_type: 'line',
      title: 'Orders by Month (Full Year)',
      data: [
        { month: 'Jan', orders: 1450 },
        { month: 'Feb', orders: 1520 },
        { month: 'Mar', orders: 1780 },
        { month: 'Apr', orders: 1610 },
        { month: 'May', orders: 1700 },
        { month: 'Jun', orders: 1650 },
        { month: 'Jul', orders: 1580 },
        { month: 'Aug', orders: 1720 },
        { month: 'Sep', orders: 1690 },
        { month: 'Oct', orders: 1850 },
        { month: 'Nov', orders: 2340 },
        { month: 'Dec', orders: 2100 },
      ],
      x_key: 'month',
      y_key: 'orders',
    },
    sql: { sql: "SELECT DATE_TRUNC('month', order_purchase_timestamp) AS month, COUNT(*) AS orders FROM orders GROUP BY month ORDER BY month", explanation: 'Monthly order count for the full year.' },
  },
  {
    match: /^repeat.*customer|customer.*loyalty|return.*customer/i,
    answer: '**8.7%** of customers are repeat buyers. The average repeat customer places **2.3 orders**.',
    sql: { sql: 'WITH customer_orders AS (SELECT customer_id, COUNT(*) AS order_count FROM orders GROUP BY customer_id) SELECT SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS repeat_rate, AVG(order_count) AS avg_orders FROM customer_orders', explanation: 'Calculating repeat customer rate and average orders per customer.' },
  },
  {
    match: /^cancel|cancellation.*rate|cancelled orders/i,
    answer: 'The cancellation rate is **0.9%**. We have 112 cancelled orders out of 12,458 total.',
    sql: { sql: "SELECT COUNT(*) * 100.0 / (SELECT COUNT(*) FROM orders) AS cancel_rate FROM orders WHERE order_status = 'canceled'", explanation: 'Calculating order cancellation rate.' },
  },
  {
    match: /^most.*popular.*category|popular.*product/i,
    answer: 'The most popular product category is **Bed Bath & Table** with 1,112 units sold, followed by **Health & Beauty** (987) and **Sports & Leisure** (856).',
    chart: {
      chart_type: 'bar',
      title: 'Most Popular Categories',
      data: [
        { category: 'Bed Bath', units: 1112 },
        { category: 'Health', units: 987 },
        { category: 'Sports', units: 856 },
        { category: 'Furniture', units: 789 },
        { category: 'Computers', units: 743 },
        { category: 'Toys', units: 654 },
        { category: 'Books', units: 543 },
      ],
      x_key: 'category',
      y_key: 'units',
    },
    sql: { sql: 'SELECT p.product_category_name, COUNT(*) AS units FROM order_items oi JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY units DESC LIMIT 7', explanation: 'Identifying top categories by units sold.' },
  },
  {
    match: /^revenue.*year|year.*revenue|annual/i,
    answer: 'Total revenue for the current year is **$13,591,840.72**. This is a **12% increase** over the previous year.',
    chart: {
      chart_type: 'line',
      title: 'Annual Revenue Comparison',
      data: [
        { month: 'Jan', current: 2100000, previous: 1850000 },
        { month: 'Feb', current: 1950000, previous: 1720000 },
        { month: 'Mar', current: 2340000, previous: 1980000 },
        { month: 'Apr', current: 2210000, previous: 2010000 },
        { month: 'May', current: 2560000, previous: 2150000 },
        { month: 'Jun', current: 2431840, previous: 2210000 },
      ],
      x_key: 'month',
      y_key: 'current',
    },
    sql: { sql: 'SELECT DATE_TRUNC(\'month\', o.order_purchase_timestamp) AS month, SUM(p.payment_value) AS revenue FROM orders o JOIN order_payments p ON o.order_id = p.order_id WHERE o.order_purchase_timestamp >= NOW() - INTERVAL \'1 year\' GROUP BY month ORDER BY month', explanation: 'Revenue trend over the current year.' },
  },
  {
    match: /^distribution.*price|price.*range|order.*price/i,
    answer: 'Order value distribution:\n- **Under $50**: 22%\n- **$50 - $100**: 31%\n- **$100 - $200**: 28%\n- **$200 - $500**: 14%\n- **Over $500**: 5%',
    chart: {
      chart_type: 'bar',
      title: 'Order Value Distribution',
      data: [
        { range: 'Under $50', pct: 22 },
        { range: '$50-$100', pct: 31 },
        { range: '$100-$200', pct: 28 },
        { range: '$200-$500', pct: 14 },
        { range: 'Over $500', pct: 5 },
      ],
      x_key: 'range',
      y_key: 'pct',
    },
    sql: { sql: 'SELECT CASE WHEN payment_value < 50 THEN \'Under $50\' WHEN payment_value < 100 THEN \'$50-$100\' WHEN payment_value < 200 THEN \'$100-$200\' WHEN payment_value < 500 THEN \'$200-$500\' ELSE \'Over $500\' END AS price_range, COUNT(*) * 100.0 / SUM(COUNT(*)) OVER() AS pct FROM order_payments GROUP BY price_range ORDER BY price_range', explanation: 'Distribution of orders by price range.' },
  },
  {
    match: /^customer.*satisfaction|satisfaction.*score/i,
    answer: 'Customer satisfaction is high — **4.1 out of 5** average rating. **72%** of reviews are 4 or 5 stars.',
    chart: {
      chart_type: 'bar',
      title: 'Satisfaction Overview',
      data: [
        { metric: 'Avg Rating', value: 4.1 },
        { metric: '5 Star %', value: 53 },
        { metric: '4 Star %', value: 24 },
        { metric: '3 Star %', value: 10 },
        { metric: '2 Star %', value: 4 },
        { metric: '1 Star %', value: 5 },
      ],
      x_key: 'metric',
      y_key: 'value',
    },
    sql: { sql: 'SELECT AVG(review_score) AS avg_rating, SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END) * 100.0 / COUNT(*) AS positive_pct FROM order_reviews', explanation: 'Calculating overall satisfaction metrics.' },
  },
  {
    match: /^product.*count|how many products|inventory/i,
    answer: 'There are **32,951** unique products across **71** categories in the catalog.',
    sql: { sql: 'SELECT COUNT(DISTINCT product_id) AS products, COUNT(DISTINCT product_category_name) AS categories FROM products', explanation: 'Counting products and categories.' },
  },
]

const CLARIFY_MATCHERS = [
  { match: /customers|show me|vague|ambiguous|help/i, question: 'Which attribute would you like to see — **count**, **list**, or by **region**?' },
  { match: /sales|revenue|how much/i, question: 'Which time period are you interested in — **this month**, **this quarter**, or **this year**?' },
  { match: /products|items|goods/i, question: 'What would you like to know about products — **top sellers**, **categories**, or **inventory count**?' },
]

export function getMockResponse(
  question: string,
  conversation_id?: string,
  clarification_answer?: string,
): AskResponse {
  if (conversation_id && clarification_answer) {
    const combined = `${question} ${clarification_answer}`
    if (combined.includes('region') || combined.includes('state')) {
      return {
        type: 'answer',
        answer: 'Orders by region:\n- **SP (São Paulo)**: 41,920 orders\n- **RJ (Rio de Janeiro)**: 13,520 orders\n- **MG (Minas Gerais)**: 11,340 orders\n- **RS (Rio Grande do Sul)**: 6,710 orders\n- **PR (Paraná)**: 5,980 orders',
        chart: {
          chart_type: 'bar',
          title: 'Orders by State',
          data: [
            { state: 'SP', orders: 41920 },
            { state: 'RJ', orders: 13520 },
            { state: 'MG', orders: 11340 },
            { state: 'RS', orders: 6710 },
            { state: 'PR', orders: 5980 },
          ],
          x_key: 'state',
          y_key: 'orders',
        },
        sql: { sql: "SELECT c.customer_state, COUNT(*) AS orders FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_state ORDER BY orders DESC LIMIT 5", explanation: 'Geographic breakdown of orders by customer state.' },
        conversation_id,
      }
    }
    if (combined.includes('count')) {
      return {
        type: 'answer',
        answer: 'The total count is **9,940 customers** and **12,458 orders**.',
        chart: null,
        sql: { sql: 'SELECT (SELECT COUNT(*) FROM customers) AS customers, (SELECT COUNT(*) FROM orders) AS orders', explanation: 'Counting total customers and orders.' },
        conversation_id,
      }
    }
    if (combined.includes('list')) {
      return {
        type: 'answer',
        answer: 'Here are the top 10 customers by order count:\n1. Customer #15983 — 12 orders\n2. Customer #20541 — 11 orders\n3. Customer #8712 — 9 orders\n4. Customer #44301 — 9 orders\n5. Customer #36789 — 8 orders\n6. Customer #11234 — 8 orders\n7. Customer #55890 — 7 orders\n8. Customer #67211 — 7 orders\n9. Customer #33451 — 6 orders\n10. Customer #78901 — 6 orders',
        chart: null,
        sql: { sql: 'SELECT c.customer_unique_id, COUNT(*) AS order_count FROM customers c JOIN orders o ON c.customer_id = o.customer_id GROUP BY c.customer_unique_id ORDER BY order_count DESC LIMIT 10', explanation: 'Top customers by order frequency.' },
        conversation_id,
      }
    }
    if (combined.includes('month')) {
      return {
        type: 'answer',
        answer: 'Revenue this month is **$2,431,840**, with total orders of **1,890**.',
        chart: {
          chart_type: 'bar',
          title: 'This Month vs Last Month',
          data: [
            { metric: 'Last Month', revenue: 2210000 },
            { metric: 'This Month', revenue: 2431840 },
          ],
          x_key: 'metric',
          y_key: 'revenue',
        },
        sql: { sql: "SELECT SUM(payment_value) AS revenue FROM order_payments p JOIN orders o ON p.order_id = o.order_id WHERE DATE_TRUNC('month', o.order_purchase_timestamp) = DATE_TRUNC('month', NOW())", explanation: 'Revenue for the current month.' },
        conversation_id,
      }
    }
    if (combined.includes('quarter')) {
      return {
        type: 'answer',
        answer: 'Revenue this quarter is **$6,701,840**, a **9% increase** over last quarter.',
        chart: {
          chart_type: 'bar',
          title: 'Quarterly Revenue',
          data: [
            { quarter: 'Q1', revenue: 6210000 },
            { quarter: 'Q2', revenue: 6701840 },
          ],
          x_key: 'quarter',
          y_key: 'revenue',
        },
        sql: { sql: "SELECT DATE_TRUNC('quarter', o.order_purchase_timestamp) AS quarter, SUM(p.payment_value) AS revenue FROM orders o JOIN order_payments p ON o.order_id = p.order_id GROUP BY quarter ORDER BY quarter DESC LIMIT 2", explanation: 'Revenue by quarter.' },
        conversation_id,
      }
    }
    if (combined.includes('year')) {
      return {
        type: 'answer',
        answer: 'Total revenue this year is **$13,591,840.72**, up **12%** year-over-year.',
        chart: {
          chart_type: 'line',
          title: 'Year-over-Year Revenue',
          data: [
            { month: 'Jan', thisYear: 2100000, lastYear: 1850000 },
            { month: 'Feb', thisYear: 1950000, lastYear: 1720000 },
            { month: 'Mar', thisYear: 2340000, lastYear: 1980000 },
            { month: 'Apr', thisYear: 2210000, lastYear: 2010000 },
            { month: 'May', thisYear: 2560000, lastYear: 2150000 },
            { month: 'Jun', thisYear: 2431840, lastYear: 2210000 },
          ],
          x_key: 'month',
          y_key: 'thisYear',
        },
        sql: { sql: 'SELECT DATE_TRUNC(\'month\', o.order_purchase_timestamp) AS month, SUM(p.payment_value) AS revenue FROM orders o JOIN order_payments p ON o.order_id = p.order_id WHERE o.order_purchase_timestamp >= NOW() - INTERVAL \'1 year\' GROUP BY month ORDER BY month', explanation: 'Year-over-year revenue comparison.' },
        conversation_id,
      }
    }
    if (combined.includes('top sellers') || combined.includes('top')) {
      return {
        type: 'answer',
        answer: 'The top-selling product categories:\n1. **Bed Bath & Table** — 1,112 units\n2. **Health & Beauty** — 987 units\n3. **Sports & Leisure** — 856 units',
        chart: {
          chart_type: 'bar',
          title: 'Top Selling Categories',
          data: [
            { category: 'Bed Bath', units: 1112 },
            { category: 'Health', units: 987 },
            { category: 'Sports', units: 856 },
            { category: 'Furniture', units: 789 },
            { category: 'Computers', units: 743 },
          ],
          x_key: 'category',
          y_key: 'units',
        },
        sql: { sql: 'SELECT p.product_category_name, COUNT(*) AS units FROM order_items oi JOIN products p ON oi.product_id = p.product_id GROUP BY p.product_category_name ORDER BY units DESC LIMIT 5', explanation: 'Top categories by units sold.' },
        conversation_id,
      }
    }
    if (combined.includes('categories')) {
      return {
        type: 'answer',
        answer: 'There are **71 product categories**. The most diverse category is **Furniture & Decor** with 2,345 unique products.',
        chart: null,
        sql: { sql: 'SELECT COUNT(DISTINCT product_category_name) AS category_count FROM products', explanation: 'Counting distinct product categories.' },
        conversation_id,
      }
    }
    if (combined.includes('inventory') || combined.includes('count')) {
      return {
        type: 'answer',
        answer: 'We have **32,951** unique products across **71** categories.',
        chart: null,
        sql: { sql: 'SELECT COUNT(*) AS total_products, COUNT(DISTINCT product_category_name) AS categories FROM products', explanation: 'Product inventory count.' },
        conversation_id,
      }
    }
    return {
      type: 'answer',
      answer: `Here are the results for "${question}" with filter "${clarification_answer}".`,
      chart: null,
      sql: { sql: `SELECT * FROM ${question.replace(/\s+/g, '_')} WHERE ${clarification_answer} IS NOT NULL LIMIT 100`, explanation: 'Query filtered by your selection.' },
      conversation_id,
    }
  }

  const q = question.toLowerCase()

  for (const entry of ENTRIES) {
    if (q.match(entry.match)) {
      return {
        type: 'answer',
        answer: entry.answer,
        chart: entry.chart ?? null,
        sql: entry.sql ?? null,
        conversation_id: null,
      }
    }
  }

  for (const clarify of CLARIFY_MATCHERS) {
    if (q.match(clarify.match)) {
      return {
        type: 'clarifying_question',
        question: clarify.question,
        options: extractOptions(clarify.question),
        conversation_id: `mock-conv-${Date.now()}`,
      }
    }
  }

  return {
    type: 'answer',
    answer: `I found **1,234 results** related to "${question}". The top result shows **$5,678** in value for the most relevant category. Would you like me to break this down further?`,
    chart: null,
    sql: null,
    conversation_id: null,
  }
}

function extractOptions(question: string): string[] {
  const match = question.match(/\*\*(.*?)\*\*/g)
  if (match) {
    return match.map((m) => m.replace(/\*\*/g, ''))
  }
  return ['count', 'list', 'region']
}

