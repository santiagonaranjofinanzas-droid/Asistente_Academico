import { TaskCard } from './task-card';
import { 
  format, isSameDay, isSameMonth, parseISO, 
  startOfMonth, endOfMonth, startOfWeek, endOfWeek, 
  eachDayOfInterval, addMonths, subMonths, isToday
} from 'date-fns';
import { es } from 'date-fns/locale';
import { ChevronLeft, ChevronRight, Calendar as CalendarIcon } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';
import { useState } from 'react';
import { Button } from './ui/button';
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetDescription } from './ui/sheet';

export function CalendarView({ tasks, onFocusTask }: { tasks: any[], onFocusTask?: (task: any) => void }) {
  const [currentDate, setCurrentDate] = useState(new Date());
  const [selectedDay, setSelectedDay] = useState<Date | null>(null);

  // Parse tasks and put them into a dictionary by 'yyyy-MM-dd'
  const groupedTasks: Record<string, any[]> = {};
  tasks.forEach((task) => {
    if (!task.fecha_entrega) return;
    const dateStr = format(parseISO(task.fecha_entrega), 'yyyy-MM-dd');
    if (!groupedTasks[dateStr]) groupedTasks[dateStr] = [];
    groupedTasks[dateStr].push(task);
  });

  const monthStart = startOfMonth(currentDate);
  const monthEnd = endOfMonth(monthStart);
  const startDate = startOfWeek(monthStart, { weekStartsOn: 1 }); // Start on Monday
  const endDate = endOfWeek(monthEnd, { weekStartsOn: 1 });

  const calendarDays = eachDayOfInterval({ start: startDate, end: endDate });
  const weekDays = ['Lun', 'Mar', 'Mié', 'Jue', 'Vie', 'Sáb', 'Dom'];

  const nextMonth = () => setCurrentDate(addMonths(currentDate, 1));
  const prevMonth = () => setCurrentDate(subMonths(currentDate, 1));
  
  const selectedDayTasks = selectedDay ? groupedTasks[format(selectedDay, 'yyyy-MM-dd')] || [] : [];

  const getStatusColor = (status: string) => {
    if (status === 'por_empezar') return 'bg-slate-500/10 text-slate-500 border-slate-500/30';
    if (status === 'en_proceso') return 'bg-blue-500/10 text-blue-500 border-blue-500/30';
    if (status === 'lista') return 'bg-green-500/10 text-green-500 border-green-500/30';
    return 'bg-purple-500/10 text-purple-500 border-purple-500/30';
  };

  return (
    <div className="space-y-6">
      {/* Header Controllers */}
      <div className="flex items-center justify-between bg-card/50 p-4 rounded-xl border border-border/50">
        <h2 className="text-xl font-bold flex items-center gap-2 capitalize">
          <CalendarIcon className="w-5 h-5 text-primary" />
          {format(currentDate, 'MMMM yyyy', { locale: es })}
        </h2>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="icon" onClick={prevMonth} className="h-8 w-8">
            <ChevronLeft className="w-4 h-4" />
          </Button>
          <Button variant="outline" size="sm" onClick={() => setCurrentDate(new Date())} className="h-8">
            Hoy
          </Button>
          <Button variant="outline" size="icon" onClick={nextMonth} className="h-8 w-8">
            <ChevronRight className="w-4 h-4" />
          </Button>
        </div>
      </div>

      {/* Grid Header (Days of week) */}
      <div className="grid grid-cols-7 gap-4">
        {weekDays.map(day => (
          <div key={day} className="text-center text-xs font-bold uppercase tracking-wider text-muted-foreground/70 pb-2 border-b border-border/50">
            {day}
          </div>
        ))}

        {/* Grid Cells */}
        <AnimatePresence mode="wait">
          <motion.div
            key={currentDate.toString()}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 10 }}
            transition={{ duration: 0.2 }}
            className="contents" // "contents" makes the children participate in the parent grid directly
          >
            {calendarDays.map((day) => {
              const dayStr = format(day, 'yyyy-MM-dd');
              const dayTasks = groupedTasks[dayStr] || [];
              const isCurrentMonth = isSameMonth(day, monthStart);
              const isCurrentDay = isToday(day);

              const total = dayTasks.length;
              const completed = dayTasks.filter(t => t.estado === 'entregada' || t.estado === 'lista').length;
              const overdue = dayTasks.filter(t => (t.estado === 'por_empezar' || t.estado === 'en_proceso') && t.fecha_entrega && isPast(new Date(t.fecha_entrega)) && !isToday(new Date(t.fecha_entrega))).length;

              // TradeZella Heatmap coloration logic
              let heatmapColor = isCurrentMonth ? 'bg-card/40 border-border/50' : 'bg-transparent border-transparent opacity-40';
              let textColor = 'text-muted-foreground';

              if (total > 0) {
                if (overdue > 0) {
                  heatmapColor = 'bg-red-500/15 border-red-500/30 hover:bg-red-500/25';
                  textColor = 'text-red-500 font-bold';
                } else if (completed === total) {
                  heatmapColor = 'bg-green-500/15 border-green-500/30 hover:bg-green-500/25';
                  textColor = 'text-green-500 font-bold';
                } else if (completed > 0) {
                  heatmapColor = 'bg-yellow-500/15 border-yellow-500/30 hover:bg-yellow-500/25';
                  textColor = 'text-yellow-600 dark:text-yellow-400 font-bold';
                } else {
                  heatmapColor = 'bg-slate-500/10 border-slate-500/20 hover:bg-slate-500/20';
                  textColor = 'text-primary font-bold';
                }
              }

              return (
                <div
                  key={day.toString()}
                  onClick={() => { if (total > 0) setSelectedDay(day); }}
                  className={`min-h-[100px] p-3 rounded-xl border transition-all duration-300 relative flex flex-col items-center justify-center gap-1
                    ${heatmapColor}
                    ${total > 0 ? 'cursor-pointer hover:shadow-md hover:scale-[1.02]' : ''}
                    ${isCurrentDay ? 'ring-2 ring-primary ring-opacity-100 ring-offset-2 ring-offset-background' : ''}
                  `}
                >
                  <span className={`text-lg transition-colors ${textColor}`}>
                    {format(day, 'd')}
                  </span>
                  
                  {total > 0 && (
                    <div className="flex flex-col items-center mt-1">
                      <span className={`text-[10px] uppercase tracking-wider opacity-80 ${textColor}`}>
                        {completed}/{total}
                      </span>
                      <div className="w-full bg-background/50 h-1 mt-1.5 rounded-full overflow-hidden">
                        <div 
                          className="h-full bg-current transition-all"
                          style={{ width: `${(completed / total) * 100}%` }}
                        />
                      </div>
                    </div>
                  )}
                </div>
              );
            })}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Day Details Modal / Sheet */}
      <Sheet open={selectedDay !== null} onOpenChange={(open) => !open && setSelectedDay(null)}>
        <SheetContent side="right" className="w-[400px] sm:w-[540px] overflow-y-auto">
          <SheetHeader className="mb-6">
            <SheetTitle className="capitalize text-2xl flex items-center gap-2">
              {selectedDay ? format(selectedDay, 'EEEE d, MMMM', { locale: es }) : ''}
            </SheetTitle>
            <SheetDescription>
              {selectedDayTasks.length} {selectedDayTasks.length === 1 ? 'tarea programada' : 'tareas programadas'} para este día.
            </SheetDescription>
          </SheetHeader>
          <div className="space-y-4 pb-12">
             {selectedDayTasks.map(task => (
               <TaskCard 
                 key={task.id} 
                 task={task} 
               />
            ))}
          </div>
        </SheetContent>
      </Sheet>
    </div>
  );
}
