import { useQuery } from '@tanstack/react-query';
import { api } from '../api';
import { LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

export default function Dashboard() {
  const { data: monthlyData, isLoading: monthlyLoading } = useQuery({
    queryKey: ['analytics', 'monthly'],
    queryFn: () => api.getMonthlyRevenue(),
  });

  const { data: topClients, isLoading: clientsLoading } = useQuery({
    queryKey: ['analytics', 'topClients'],
    queryFn: () => api.getTopClients(5),
  });

  const { data: aging, isLoading: agingLoading } = useQuery({
    queryKey: ['analytics', 'aging'],
    queryFn: () => api.getAgingBuckets(),
  });

  const formatCurrency = (value: number) => `₹${value.toLocaleString('en-IN', { minimumFractionDigits: 2 })}`;

  return (
    <div className="p-8">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-gray-900">Dashboard</h1>
        <p className="text-gray-600 mt-1">Overview of your billing and invoicing</p>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Revenue (Last 12 Months)</h3>
          {monthlyLoading ? (
            <div className="spinner mt-2"></div>
          ) : (
            <p className="text-3xl font-bold text-primary-600 mt-2">
              {formatCurrency(monthlyData?.reduce((sum, item) => sum + item.revenue, 0) || 0)}
            </p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Total Invoices</h3>
          {monthlyLoading ? (
            <div className="spinner mt-2"></div>
          ) : (
            <p className="text-3xl font-bold text-primary-600 mt-2">
              {monthlyData?.reduce((sum, item) => sum + item.invoice_count, 0) || 0}
            </p>
          )}
        </div>

        <div className="bg-white rounded-lg shadow p-6">
          <h3 className="text-sm font-medium text-gray-500">Average Invoice Value</h3>
          {monthlyLoading ? (
            <div className="spinner mt-2"></div>
          ) : (
            <p className="text-3xl font-bold text-primary-600 mt-2">
              {formatCurrency(
                monthlyData && monthlyData.length > 0
                  ? monthlyData.reduce((sum, item) => sum + item.revenue, 0) /
                    monthlyData.reduce((sum, item) => sum + item.invoice_count, 0)
                  : 0
              )}
            </p>
          )}
        </div>
      </div>

      {/* Monthly Revenue Chart */}
      <div className="bg-white rounded-lg shadow p-6 mb-8">
        <h2 className="text-xl font-semibold mb-4">Monthly Revenue Trend</h2>
        {monthlyLoading ? (
          <div className="flex justify-center py-12">
            <div className="spinner"></div>
          </div>
        ) : (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={monthlyData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="month" />
              <YAxis tickFormatter={(value) => `₹${value/1000}k`} />
              <Tooltip formatter={(value: number) => formatCurrency(value)} />
              <Legend />
              <Line type="monotone" dataKey="revenue" stroke="#2563eb" strokeWidth={2} name="Revenue" />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        {/* Top Clients */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Top 5 Clients</h2>
          {clientsLoading ? (
            <div className="flex justify-center py-12">
              <div className="spinner"></div>
            </div>
          ) : (
            <ResponsiveContainer width="100%" height={300}>
              <BarChart data={topClients} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis type="number" tickFormatter={(value) => `₹${value/1000}k`} />
                <YAxis dataKey="client_name" type="category" width={150} />
                <Tooltip formatter={(value: number) => formatCurrency(value)} />
                <Bar dataKey="total_revenue" fill="#2563eb" name="Revenue" />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Aging Analysis */}
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-xl font-semibold mb-4">Aging Analysis (Unpaid)</h2>
          {agingLoading ? (
            <div className="flex justify-center py-12">
              <div className="spinner"></div>
            </div>
          ) : (
            <div className="space-y-4 mt-6">
              <div className="flex justify-between items-center p-4 bg-green-50 rounded-lg">
                <span className="font-medium text-green-900">0-30 Days</span>
                <span className="text-lg font-bold text-green-700">
                  {formatCurrency(aging?.bucket_0_30 || 0)}
                </span>
              </div>
              <div className="flex justify-between items-center p-4 bg-yellow-50 rounded-lg">
                <span className="font-medium text-yellow-900">31-60 Days</span>
                <span className="text-lg font-bold text-yellow-700">
                  {formatCurrency(aging?.bucket_31_60 || 0)}
                </span>
              </div>
              <div className="flex justify-between items-center p-4 bg-red-50 rounded-lg">
                <span className="font-medium text-red-900">61+ Days</span>
                <span className="text-lg font-bold text-red-700">
                  {formatCurrency(aging?.bucket_61_plus || 0)}
                </span>
              </div>
              <div className="flex justify-between items-center p-4 bg-gray-100 rounded-lg border-t-2 border-gray-300">
                <span className="font-bold text-gray-900">Total Unpaid</span>
                <span className="text-xl font-bold text-gray-900">
                  {formatCurrency((aging?.bucket_0_30 || 0) + (aging?.bucket_31_60 || 0) + (aging?.bucket_61_plus || 0))}
                </span>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
