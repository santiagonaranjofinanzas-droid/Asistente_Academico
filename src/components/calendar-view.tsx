import { TaskCard } from './task-card';
import { format, isSameDay, parseISO } from 'date-fns';
import { es } from 'date-fns/locale';
import { Calendar as CalendarIcon, Clock } from 'lucide-react';
import { motion } from 'framer-motion';

export function CalendarView({ tasks, onFocusTask }: { tasks: any[], onFocusTask?: (task: any) => void }) {
  // Group tasks by date
  const groupedTasks: Record<string, any[]> = {};
  const noDateTasks: any[] = [];

  tasks.forEach((task) => {
    if (!task.fecha_entrega) {
      noDateTasks.push(task);
      return;
    }
    const dateStr = format(parseISO(task.fecha_entrega), 'yyyy-MM-dd');
    if (!groupedTasks[dateStr]) groupedTasks[dateStr] = [];
    groupedTasks[dateStr].push(task);
  });

  // Sort dates
  const sortedDates = Object.keys(groupedTasks).sort((a, b) => new Date(a).getTime() - new Date(b).getTime());

  return (
    <div className="space-y-12 pb-12">
      {sortedDates.map((dateStr, idx) => {
        const dateTasks = groupedTasks[dateStr];
        const displayDate = parseISO(dateStr);
        const isToday = isSameDay(displayDate, new Date());

        return (
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            key={dateStr} 
            className="relative"
          >
            {/* Timeline Line */}
            <div className="absolute left-6 top-8 bottom-[-48px] w-0.5 bg-border -z-10" />

            <div className="flex gap-6 items-start">
              <div className={`mt-1 flex-shrink-0 w-12 h-12 rounded-full border-4 border-background flex items-center justify-center ${isToday ? 'bg-primary text-primary-foreground shadow-lg shadow-primary/20' : 'bg-muted text-muted-foreground'}`}>
                {isToday ? <Clock className="w-5 h-5" /> : <CalendarIcon className="w-5 h-5" />}
              </div>
              
              <div className="flex-1 space-y-4">
                <h3 className="text-xl font-bold flex items-center gap-2">
                  <span className="capitalize">{format(displayDate, 'EEEE d', { locale: es })}</span>
                  <span className="text-muted-foreground font-normal text-sm">
                    de {format(displayDate, 'MMMM, yyyy', { locale: es })}
                  </span>
                  {isToday && <span className="text-[10px] bg-primary text-primary-foreground px-2 py-0.5 rounded-full uppercase tracking-wider font-bold ml-2">Hoy</span>}
                </h3>
                
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                  {dateTasks.map(task => (
                    <TaskCard key={task.id} task={task} onFocus={onFocusTask ? () => onFocusTask(task) : undefined} />
                  ))}
                </div>
              </div>
            </div>
          </motion.div>
        );
      })}

      {noDateTasks.length > 0 && (
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="relative pt-8"
        >
          <div className="flex gap-6 items-start opacity-70">
            <div className="mt-1 flex-shrink-0 w-12 h-12 rounded-full border-4 border-background flex items-center justify-center bg-muted text-muted-foreground">
              <Clock className="w-5 h-5" />
            </div>
            <div className="flex-1 space-y-4">
              <h3 className="text-lg font-bold text-muted-foreground">Sin Fecha de Entrega</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                {noDateTasks.map(task => (
                  <TaskCard key={task.id} task={task} onFocus={onFocusTask ? () => onFocusTask(task) : undefined} />
                ))}
              </div>
            </div>
          </div>
        </motion.div>
      )}

      {tasks.length === 0 && (
        <div className="py-24 text-center space-y-4 text-muted-foreground">
          <CalendarIcon className="w-12 h-12 mx-auto opacity-20" />
          <p>No tienes tareas pendientes en tu calendario.</p>
        </div>
      )}
    </div>
  );
}
