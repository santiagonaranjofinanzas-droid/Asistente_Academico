import { Card } from './ui/card';
import { Target, CheckCircle, CalendarDays, Clock } from 'lucide-react';
import { differenceInDays, isBefore, addDays } from 'date-fns';

export function AnalyticsHeader({ tasks }: { tasks: any[] }) {
  // Advanced Metric: Materia Más Cargada
  const activeTasks = tasks.length;
  const materiaCounts: Record<string, number> = {};
  
  tasks.forEach(t => {
    if (t.materia) materiaCounts[t.materia] = (materiaCounts[t.materia] || 0) + 1;
  });
  
  let maxMateria = 'Ninguna';
  let maxCount = 0;
  for (const [materia, count] of Object.entries(materiaCounts)) {
    if (count > maxCount) {
      maxCount = count;
      maxMateria = materia;
    }
  }

  const now = new Date();
  const next7Days = addDays(now, 7);

  const proximas = tasks.filter((t) => {
    if (!t.fecha_entrega || t.estado === 'lista' || t.archivada) return false;
    const due = new Date(t.fecha_entrega);
    return isBefore(due, next7Days) && isBefore(now, due);
  }).length;

  const vencidas = tasks.filter((t) => {
    if (!t.fecha_entrega || t.estado === 'lista' || t.archivada) return false;
    return isBefore(new Date(t.fecha_entrega), now);
  }).length;

  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-8">
      <Card className="p-4 glass-card flex items-center gap-4">
        <div className="p-3 bg-primary/10 rounded-full text-primary">
          <Target className="w-5 h-5" />
        </div>
        <div className="overflow-hidden">
          <p className="text-sm text-muted-foreground font-medium truncate">Tareas Activas</p>
          <h3 className="text-2xl font-bold">{activeTasks}</h3>
        </div>
      </Card>

      <Card className="p-4 glass-card flex items-center gap-4">
        <div className="p-3 bg-purple-500/10 rounded-full text-purple-500">
          <CheckCircle className="w-5 h-5" />
        </div>
        <div className="overflow-hidden w-full">
          <p className="text-sm text-muted-foreground font-medium truncate">Foco Principal</p>
          <h3 className="text-base font-bold truncate mt-1" title={maxMateria}>{maxMateria}</h3>
          <span className="text-[10px] text-muted-foreground">{maxCount} tareas pendientes</span>
        </div>
      </Card>

      <Card className="p-4 glass-card flex items-center gap-4">
        <div className="p-3 bg-blue-500/10 rounded-full text-blue-500">
          <CalendarDays className="w-5 h-5" />
        </div>
        <div className="overflow-hidden">
          <p className="text-sm text-muted-foreground font-medium truncate">Próximos 7 días</p>
          <h3 className="text-2xl font-bold">{proximas}</h3>
        </div>
      </Card>

      <Card className="p-4 glass-card flex items-center gap-4">
        <div className={`p-3 rounded-full ${vencidas > 0 ? 'bg-destructive/10 text-destructive' : 'bg-muted text-muted-foreground'}`}>
          <Clock className="w-5 h-5" />
        </div>
        <div className="overflow-hidden">
          <p className="text-sm text-muted-foreground font-medium truncate">Vencidas</p>
          <h3 className={`text-2xl font-bold ${vencidas > 0 ? 'text-destructive' : ''}`}>{vencidas}</h3>
        </div>
      </Card>
    </div>
  );
}
