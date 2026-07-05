import type { ChartSpecResponse } from '../../types/api'
import {
  BarChart, LineChart, Bar, Line,
  XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
} from 'recharts'

interface ChartWidgetProps {
  chart: ChartSpecResponse
}

function renderChart(chart: ChartSpecResponse) {
  const { chart_type, data, x_key, y_key } = chart

  if (chart_type === 'bar') {
    return (
      <BarChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={x_key} />
        <YAxis />
        <Tooltip />
        <Legend />
        <Bar dataKey={y_key} fill="#8884d8" />
      </BarChart>
    )
  }

  if (chart_type === 'line') {
    return (
      <LineChart data={data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={x_key} />
        <YAxis />
        <Tooltip />
        <Legend />
        <Line type="monotone" dataKey={y_key} stroke="#8884d8" />
      </LineChart>
    )
  }

  return (
    <BarChart data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey={x_key} />
      <YAxis />
      <Tooltip />
      <Legend />
      <Bar dataKey={y_key} fill="#82ca9d" />
    </BarChart>
  )
}

export function ChartWidget({ chart }: ChartWidgetProps) {
  const { title } = chart

  return (
    <div className="chart-widget">
      <h4>{title}</h4>
      <ResponsiveContainer width="100%" height={300}>
        {renderChart(chart)}
      </ResponsiveContainer>
    </div>
  )
}
