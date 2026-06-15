import { useState, useEffect } from 'react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../contexts/AuthContext';
import { api } from '../api';
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis,
  Tooltip, ResponsiveContainer, CartesianGrid,
} from 'recharts';
import WelcomePreferencesModal from '../components/WelcomePreferencesModal';
import { TrendingUp, FileText, IndianRupee } from 'lucide-react';

/* -------------------------------------------------------------------------- */
/* Formatters                                                                 */
/* -------------------------------------------------------------------------- */

const formatINR = (value: number) =>
  '₹' + value.toLocaleString('en-IN', {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });

const formatINRCompact = (value: number) => {
  if (value >= 10000000) return `₹${(value / 10000000).toFixed(1)}Cr`;
  if (value >= 100000)   return `₹${(value / 100000).toFixed(1)}L`;
  if (value >= 1000)     return `₹${(value / 1000).toFixed(1)}k`;
  return `₹${value.toFixed(0)}`;
};

/* -------------------------------------------------------------------------- */
/* Metric tile — editorial number plate                                       */
/* -------------------------------------------------------------------------- */

function Metric({
  eyebrow,
  value,
  caption,
  Icon,
  isLoading,
  accent = false,
}: {
  eyebrow: string;
  value: string;
  caption?: string;
  Icon: typeof IndianRupee;
  isLoading?: boolean;
  accent?: boolean;
}) {
  return (
    <div className="card p-6 relative overflow-hidden">
      {accent && (
        <div className="absolute top-0 left-0 right-0 h-[2px] bg-oxblood" />
      )}

      <div className="flex items-start justify-between">
        <div className="eyebrow">{eyebrow}</div>
        <Icon size={16} strokeWidth={1.5} className="text-ink-faint" />
      </div>

      {isLoading ? (
        <div className="h-10 mt-4 flex items-center"><div className="spinner" /></div>
      ) : (
        <div
          className="number-plate text-4xl mt-3 tabular"
          style={{ fontVariationSettings: '"opsz" 144, "wght" 500, "SOFT" 30' }}
        >
          {value}
        </div>
      )}

      {caption && (
        <div className="mt-2 text-xs text-ink-muted">{caption}</div>
      )}
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Aging row                                                                  */
/* -------------------------------------------------------------------------- */

function AgingRow({
  label, amount, tone, share,
}: {
  label: string;
  amount: number;
  tone: 'paid' | 'pending' | 'overdue' | 'draft';
  share: number;
}) {
  const toneToBar = {
    paid:    'bg-status-paid',
    pending: 'bg-status-pending',
    overdue: 'bg-status-overdue',
    draft:   'bg-status-draft',
  } as const;
  const toneToPill = {
    paid:    'pill-paid',
    pending: 'pill-pending',
    overdue: 'pill-overdue',
    draft:   'pill-draft',
  } as const;

  return (
    <div className="py-3.5 border-b border-rule-soft last:border-b-0">
      <div className="flex items-baseline justify-between">
        <span className={toneToPill[tone]}>{label}</span>
        <span className="font-mono text-sm text-ink tabular">{formatINR(amount)}</span>
      </div>
      <div className="mt-2.5 h-[2px] bg-paper-deep rounded-full overflow-hidden">
        <div
          className={`h-full ${toneToBar[tone]} transition-[width] duration-700 ease-out`}
          style={{ width: `${Math.max(2, share * 100)}%` }}
        />
      </div>
    </div>
  );
}

/* -------------------------------------------------------------------------- */
/* Dashboard                                                                  */
/* -------------------------------------------------------------------------- */

export default function Dashboard() {
  const { firm } = useAuth();
  const [showWelcomeModal, setShowWelcomeModal] = useState(false);

  useEffect(() => {
    if (firm?.created_at) {
      const createdAt = new Date(firm.created_at);
      const diffMin = (Date.now() - createdAt.getTime()) / 1000 / 60;
      const seen = localStorage.getItem('hasSeenWelcome');
      if (diffMin < 2 && !seen) setShowWelcomeModal(true);
    }
  }, [firm]);

  const handleCloseWelcome = () => {
    setShowWelcomeModal(false);
    localStorage.setItem('hasSeenWelcome', 'true');
  };

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

  // Derived metrics
  const totalRevenue   = monthlyData?.reduce((s, m) => s + m.revenue, 0) ?? 0;
  const totalInvoices  = monthlyData?.reduce((s, m) => s + m.invoice_count, 0) ?? 0;
  const avgInvoice     = totalInvoices > 0 ? totalRevenue / totalInvoices : 0;
  const totalUnpaid    = (aging?.bucket_0_30 ?? 0) +
                         (aging?.bucket_31_60 ?? 0) +
                         (aging?.bucket_61_plus ?? 0);
  const agingShare = (n: number) => (totalUnpaid > 0 ? n / totalUnpaid : 0);

  // Greeting based on time of day
  const hour = new Date().getHours();
  const greeting =
    hour < 12 ? 'Good morning' :
    hour < 17 ? 'Good afternoon' :
                'Good evening';
  const firmFirstWord = firm?.firm_name?.split(/\s+/)[0];

  // Today's date, formatted editorial-style
  const today = new Date().toLocaleDateString('en-IN', {
    weekday: 'long',
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-10 stagger">
      {/* ---- Page header ------------------------------------------------- */}
      <header className="flex items-end justify-between flex-wrap gap-6 mb-12">
        <div>
          <div className="page-eyebrow">Folio I · Dashboard</div>
          <h1 className="page-title">
            {greeting}{firmFirstWord ? `, ${firmFirstWord}.` : '.'}
          </h1>
          <p className="page-subtitle">
            A summary of your practice's billing for the trailing twelve months.
          </p>
        </div>
        <div className="text-right">
          <div className="eyebrow">As of</div>
          <div className="font-display text-lg text-ink-soft mt-1"
               style={{ fontVariationSettings: '"opsz" 48, "wght" 400, "SOFT" 30' }}>
            {today}
          </div>
        </div>
      </header>

      {/* ---- Key Metrics ------------------------------------------------- */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-px bg-rule mb-12 border border-rule">
        <Metric
          eyebrow="Trailing 12-month revenue"
          value={formatINRCompact(totalRevenue)}
          caption={isFinite(totalRevenue) ? formatINR(totalRevenue) : undefined}
          Icon={IndianRupee}
          isLoading={monthlyLoading}
          accent
        />
        <Metric
          eyebrow="Invoices issued"
          value={totalInvoices.toLocaleString('en-IN')}
          caption="Across all clients"
          Icon={FileText}
          isLoading={monthlyLoading}
        />
        <Metric
          eyebrow="Average invoice value"
          value={formatINRCompact(avgInvoice)}
          caption={avgInvoice > 0 ? formatINR(avgInvoice) : undefined}
          Icon={TrendingUp}
          isLoading={monthlyLoading}
        />
      </section>

      {/* ---- Revenue trend ---------------------------------------------- */}
      <section className="card p-8 mb-12">
        <div className="flex items-baseline justify-between mb-6">
          <div>
            <div className="eyebrow text-oxblood">Plate I</div>
            <h2 className="section-title mt-1">Revenue, by month</h2>
          </div>
          <div className="text-xs text-ink-muted">Last 12 months</div>
        </div>

        {monthlyLoading ? (
          <div className="h-[300px] flex items-center justify-center"><div className="spinner" /></div>
        ) : (
          <div className="-mx-2">
            <ResponsiveContainer width="100%" height={300}>
              <LineChart data={monthlyData} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#E8E2D2" strokeDasharray="0" vertical={false} />
                <XAxis
                  dataKey="month"
                  stroke="#9A9082"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fill: '#6B6358' }}
                />
                <YAxis
                  stroke="#9A9082"
                  tickFormatter={formatINRCompact}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fill: '#6B6358' }}
                  width={64}
                />
                <Tooltip
                  formatter={(value: number) => [formatINR(value), 'Revenue']}
                  contentStyle={{
                    background: '#FFFFFF',
                    border: '1px solid #D8D2C5',
                    borderRadius: '3px',
                    fontFamily: 'Public Sans, sans-serif',
                    fontSize: '12px',
                    boxShadow: '0 10px 40px -10px rgba(28, 24, 20, 0.15)',
                  }}
                  labelStyle={{ color: '#6B6358', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}
                  cursor={{ stroke: '#7A2E2E', strokeWidth: 1, strokeDasharray: '4 4' }}
                />
                <Line
                  type="monotone"
                  dataKey="revenue"
                  stroke="#7A2E2E"
                  strokeWidth={1.75}
                  dot={{ fill: '#7A2E2E', r: 3, strokeWidth: 0 }}
                  activeDot={{ fill: '#7A2E2E', r: 5, stroke: '#F8F4EC', strokeWidth: 2 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

      {/* ---- Two-column: top clients + aging ---------------------------- */}
      <section className="grid grid-cols-1 lg:grid-cols-5 gap-8">
        {/* Top clients */}
        <div className="card p-8 lg:col-span-3">
          <div className="flex items-baseline justify-between mb-6">
            <div>
              <div className="eyebrow text-oxblood">Plate II</div>
              <h2 className="section-title mt-1">Principal clients</h2>
            </div>
            <div className="text-xs text-ink-muted">By revenue</div>
          </div>

          {clientsLoading ? (
            <div className="h-[280px] flex items-center justify-center"><div className="spinner" /></div>
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart data={topClients} layout="vertical" margin={{ top: 4, right: 24, left: 0, bottom: 0 }}>
                <CartesianGrid stroke="#E8E2D2" strokeDasharray="0" horizontal={false} />
                <XAxis
                  type="number"
                  tickFormatter={formatINRCompact}
                  stroke="#9A9082"
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 11, fontFamily: 'JetBrains Mono, monospace', fill: '#6B6358' }}
                />
                <YAxis
                  dataKey="client_name"
                  type="category"
                  stroke="#9A9082"
                  width={140}
                  tickLine={false}
                  axisLine={false}
                  tick={{ fontSize: 12, fontFamily: 'Public Sans, sans-serif', fill: '#1C1814' }}
                />
                <Tooltip
                  formatter={(value: number) => [formatINR(value), 'Revenue']}
                  contentStyle={{
                    background: '#FFFFFF',
                    border: '1px solid #D8D2C5',
                    borderRadius: '3px',
                    fontFamily: 'Public Sans, sans-serif',
                    fontSize: '12px',
                  }}
                  cursor={{ fill: '#F1EBDC' }}
                />
                <Bar dataKey="total_revenue" fill="#7A2E2E" radius={[0, 2, 2, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>

        {/* Aging analysis */}
        <div className="card p-8 lg:col-span-2">
          <div className="mb-6">
            <div className="eyebrow text-oxblood">Plate III</div>
            <h2 className="section-title mt-1">Outstanding receivables</h2>
          </div>

          {agingLoading ? (
            <div className="h-[280px] flex items-center justify-center"><div className="spinner" /></div>
          ) : (
            <>
              <AgingRow label="0–30 Days"   amount={aging?.bucket_0_30   ?? 0} tone="paid"    share={agingShare(aging?.bucket_0_30   ?? 0)} />
              <AgingRow label="31–60 Days"  amount={aging?.bucket_31_60  ?? 0} tone="pending" share={agingShare(aging?.bucket_31_60  ?? 0)} />
              <AgingRow label="61+ Days"    amount={aging?.bucket_61_plus ?? 0} tone="overdue" share={agingShare(aging?.bucket_61_plus ?? 0)} />

              <div className="mt-5 pt-5 border-t border-rule-strong flex items-baseline justify-between">
                <div className="eyebrow">Total outstanding</div>
                <div className="font-display tabular text-2xl text-ink"
                     style={{ fontVariationSettings: '"opsz" 144, "wght" 500, "SOFT" 30' }}>
                  {formatINR(totalUnpaid)}
                </div>
              </div>
            </>
          )}
        </div>
      </section>

      {showWelcomeModal && <WelcomePreferencesModal onClose={handleCloseWelcome} />}
    </div>
  );
}
