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
      <Card className="p-3 sm:p-4 glass-card flex items-center gap-3 sm:gap-4">
        <div className="p-2 sm:p-3 bg-primary/10 rounded-full text-primary shrink-0">
          <Target className="w-4 h-4 sm:w-5 sm:h-5" />
        </div>
        <div className="overflow-hidden">
          <p className="text-[10px] sm:text-sm text-muted-foreground font-medium truncate uppercase tracking-wider sm:normal-case sm:tracking-normal">Tareas</p>
          <h3 className="text-xl sm:text-2xl font-bold leading-tight">{activeTasks}</h3>
        </div>
      </Card>

      <Card className="p-3 sm:p-4 glass-card flex items-center gap-3 sm:gap-4">
        <div className="p-2 sm:p-3 bg-purple-500/10 rounded-full text-purple-500 shrink-0">
          <CheckCircle className="w-4 h-4 sm:w-5 sm:h-5" />
        </div>
        <div className="overflow-hidden w-full">
          <p className="text-[10px] sm:text-sm text-muted-foreground font-medium truncate uppercase tracking-wider sm:normal-case sm:tracking-normal">Foco</p>
          <h3 className="text-xs sm:text-base font-bold truncate mt-0.5 sm:mt-1" title={maxMateria}>{maxMateria}</h3>
          <span className="hidden sm:inline text-[10px] text-muted-foreground">{maxCount} tareas pendientes</span>
        </div>
      </Card>

      <Card className="p-3 sm:p-4 glass-card flex items-center gap-3 sm:gap-4">
        <div className="p-2 sm:p-3 bg-blue-500/10 rounded-full text-blue-500 shrink-0">
          <CalendarDays className="w-4 h-4 sm:w-5 sm:h-5" />
        </div>
        <div className="overflow-hidden">
          <p className="text-[10px] sm:text-sm text-muted-foreground font-medium truncate uppercase tracking-wider sm:normal-case sm:tracking-normal">Semana</p>
          <h3 className="text-xl sm:text-2xl font-bold leading-tight">{proximas}</h3>
        </div>
      </Card>

      <Card className="p-3 sm:p-4 glass-card flex items-center gap-3 sm:gap-4">
        <div className={`p-2 sm:p-3 rounded-full shrink-0 ${vencidas > 0 ? 'bg-destructive/10 text-destructive' : 'bg-muted text-muted-foreground'}`}>
          <Clock className="w-4 h-4 sm:w-5 sm:h-5" />
        </div>
        <div className="overflow-hidden">
          <p className="text-[10px] sm:text-sm text-muted-foreground font-medium truncate uppercase tracking-wider sm:normal-case sm:tracking-normal">Vencidas</p>
          <h3 className={`text-xl sm:text-2xl font-bold leading-tight ${vencidas > 0 ? 'text-destructive' : ''}`}>{vencidas}</h3>
        </div>
      </Card>
    </div>
  );
}
