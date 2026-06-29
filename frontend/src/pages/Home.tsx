import { useAuth } from '../contexts/AuthContext';
import SetupChecklist from '../components/SetupChecklist';

function istHour(): number {
  const utcMs = Date.now() + new Date().getTimezoneOffset() * 60000;
  return new Date(utcMs + 5.5 * 3600000).getHours();
}

function greetingFor(h: number): string {
  if (h >= 5 && h < 12) return 'Good morning';
  if (h >= 12 && h < 17) return 'Good afternoon';
  if (h >= 17 && h < 21) return 'Good evening';
  return 'Good night';
}

export default function Home() {
  const { user, firm } = useAuth();
  const raw = firm?.firm_name || (user?.email ? user.email.split('@')[0] : 'there');
  const name = raw.charAt(0).toUpperCase() + raw.slice(1);

  return (
    <div className="max-w-page mx-auto px-8 lg:px-12 py-24">
      <div className="page-eyebrow">{new Date().toLocaleDateString('en-IN', { weekday: 'long', day: 'numeric', month: 'long' })}</div>
      <h1 className="font-display text-4xl md:text-5xl text-ink mt-2 mb-10">
        {greetingFor(istHour())}, {name}.
      </h1>
      <SetupChecklist />
    </div>
  );
}
