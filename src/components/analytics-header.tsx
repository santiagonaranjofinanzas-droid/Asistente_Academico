import { Card } from './ui/card';
import { Target, CheckCircle, CalendarDays, Clock } from 'lucide-react';
import { differenceInDays, isBefore, addDays } from 'date-fns';

export function AnalyticsHeader({ tasks }: { tasks: any[] }) {
  const total = tasks.length;
  const completadas = tasks.filter((t) => t.estado === 'lista').length;
  const progreso = total > 0 ? Math.round((completadas / total) * 100) : 0;

  const now = new Date();
  const next7Days = addDays(now, 7);

  const proximas = tasks.filter((t) => {
    if (!t.fecha_entrega || t.estado === 'lista') return false;
    const due = new Date(t.fecha_entrega);
    return isBefore(due, next7Days) && isBefore(now, due);
  }).length;

  const vencidas = tasks.filter((t) => {
    if (!t.fecha_entrega || t.estado === 'lista') return false;
    return isBefore(new Date(t.fecha_entrega), now);
  }).length;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <Card className="p-4 glass-card flex items-center gap-4">
        <div className="p-3 bg-primary/10 rounded-full text-primary">
          <Target className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground font-medium">Progreso Global</p>
          <div className="flex items-baseline gap-2">
            <h3 className="text-2xl font-bold">{progreso}%</h3>
            <span className="text-xs text-muted-foreground">{completadas}/{total}</span>
          </div>
        </div>
      </Card>

      <Card className="p-4 glass-card flex items-center gap-4">
        <div className="p-3 bg-emerald-500/10 rounded-full text-emerald-500">
          <CheckCircle className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground font-medium">Completadas</p>
          <h3 className="text-2xl font-bold">{completadas}</h3>
        </div>
      </Card>

      <Card className="p-4 glass-card flex items-center gap-4">
        <div className="p-3 bg-blue-500/10 rounded-full text-blue-500">
          <CalendarDays className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground font-medium">Próximos 7 días</p>
          <h3 className="text-2xl font-bold">{proximas}</h3>
        </div>
      </Card>

      <Card className="p-4 glass-card flex items-center gap-4">
        <div className={`p-3 rounded-full ${vencidas > 0 ? 'bg-destructive/10 text-destructive' : 'bg-muted text-muted-foreground'}`}>
          <Clock className="w-5 h-5" />
        </div>
        <div>
          <p className="text-sm text-muted-foreground font-medium">Vencidas</p>
          <h3 className={`text-2xl font-bold ${vencidas > 0 ? 'text-destructive' : ''}`}>{vencidas}</h3>
        </div>
      </Card>
    </div>
  );
}
