'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { TaskCard } from '@/components/task-card';
import { Button } from '@/components/ui/button';
import { AnalyticsHeader } from '@/components/analytics-header';
import { CalendarView } from '@/components/calendar-view';
import { Archive, LayoutGrid, List, Sparkles, CalendarDays } from 'lucide-react';
import { ThemeToggle } from '@/components/theme-toggle';
import { motion, AnimatePresence } from 'framer-motion';

export default function Dashboard() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [view, setView] = useState<'kanban' | 'list' | 'calendar' | 'archived'>('kanban');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks();

    // Subscribe to Realtime changes
    const channel = supabase
      .channel('tasks_channel')
      .on(
        'postgres_changes' as any,
        { event: '*', table: 'tareas' },
        (payload: any) => {
          console.log('Change received!', payload);
          if (payload.eventType === 'INSERT' && !payload.new.archivada) {
            setTasks((prev) => [payload.new, ...prev]);
          } else if (payload.eventType === 'UPDATE') {
            if (payload.new.archivada) {
              setTasks((prev) => prev.filter((t) => t.id !== payload.new.id));
            } else {
              setTasks((prev) => prev.map((t) => (t.id === payload.new.id ? payload.new : t)));
            }
          } else if (payload.eventType === 'DELETE') {
            setTasks((prev) => prev.filter((t) => t.id === payload.old.id));
          }
        }
      )
      .subscribe();

    return () => {
      supabase.removeChannel(channel);
    };
  }, []);

  async function fetchTasks() {
    setLoading(true);
    let query = supabase.from('tareas').select('*');
    
    if (view === 'archived') {
      query = query.eq('archivada', true);
    } else {
      query = query.eq('archivada', false);
    }

    const { data, error } = await query
      .order('fecha_entrega', { ascending: true, nullsFirst: false })
      .order('creado_at', { ascending: false });

    if (data) setTasks(data);
    setLoading(false);
  }

  // Reload tasks when view changes to archived/back
  useEffect(() => {
    fetchTasks();
  }, [view]);

  const columns = ['por_empezar', 'en_proceso', 'lista'];

  const handleDrop = async (e: React.DragEvent<HTMLElement>, newEstado: string) => {
    e.preventDefault();
    const taskId = e.dataTransfer.getData('taskId');
    if (!taskId) return;

    // Optimistic UI update
    setTasks(prev => prev.map(t => t.id === taskId ? { ...t, estado: newEstado, archivada: newEstado === 'lista' } : t));

    // Supabase update
    const updateData: any = { estado: newEstado };
    if (newEstado === 'lista') {
      updateData.archivada = true;
      updateData.estado = 'entregada'; // Final state
    }

    const { error } = await supabase
      .from('tareas')
      .update(updateData)
      .eq('id', taskId);

    if (error) {
      console.error('Error updating task status:', error);
      fetchTasks(); // Revert on error
    }
  };

  const getColColor = (col: string) => {
    if (col === 'por_empezar') return 'bg-slate-500/5 hover:bg-slate-500/10 border-slate-500/10';
    if (col === 'en_proceso') return 'bg-blue-500/5 hover:bg-blue-500/10 border-blue-500/10';
    if (col === 'lista') return 'bg-green-500/5 hover:bg-green-500/10 border-green-500/10';
    return 'bg-muted/30';
  };

  return (
    <main className="min-h-screen bg-background p-6 md:p-12">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <header className="flex flex-col md:flex-row justify-between items-start md:items-center gap-4 mb-12">
          <div>
            <h1 className="text-3xl font-bold tracking-tight mb-1 flex items-center gap-2">
              <Sparkles className="w-6 h-6 text-primary" />
              Asistente Académico
            </h1>
            <p className="text-muted-foreground text-sm font-medium">
              Gestión inteligente de tareas y recursos universitarios.
            </p>
          </div>

          <div className="flex items-center gap-2 bg-muted/50 p-1 rounded-lg border">
            <Button
              variant={view === 'kanban' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setView('kanban')}
              className="h-8 px-3"
            >
              <LayoutGrid className="w-4 h-4 mr-2" />
              Tablero
            </Button>
            <Button
              variant={view === 'list' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setView('list')}
              className="h-8 px-3"
            >
              <List className="w-4 h-4 mr-2" />
              Lista
            </Button>
            <Button
              variant={view === 'calendar' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setView('calendar')}
              className="h-8 px-3"
            >
              <CalendarDays className="w-4 h-4 mr-2" />
              Calendario
            </Button>
            <Button
              variant={view === 'archived' ? 'secondary' : 'ghost'}
              size="sm"
              onClick={() => setView('archived')}
              className="h-8 px-3"
            >
              <Archive className="w-4 h-4 mr-2" />
              Archivados
            </Button>
            <div className="w-px h-4 bg-border mx-1"></div>
            <ThemeToggle />
          </div>
        </header>

        <AnalyticsHeader tasks={tasks} />

        {/* Dashboard Content */}
        {loading ? (
          <div className="flex items-center justify-center h-64 opacity-50">
            <p className="animate-pulse font-medium">Cargando tareas...</p>
          </div>
        ) : view === 'calendar' ? (
          <CalendarView tasks={tasks} />
        ) : view === 'list' ? (
          <div className="space-y-12">
            {[
              { label: 'Lunes', index: 1 },
              { label: 'Martes', index: 2 },
              { label: 'Miércoles', index: 3 },
              { label: 'Jueves', index: 4 },
              { label: 'Viernes', index: 5 },
              { label: 'Sábado', index: 6 },
              { label: 'Domingo', index: 0 },
              { label: 'Sin fecha', index: -1 }
            ].map((day) => {
              const dayTasks = tasks.filter((t) => {
                if (!t.fecha_entrega) return day.index === -1;
                const d = new Date(t.fecha_entrega);
                // getDay() returns 0 for Sunday, 1 for Monday...
                return d.getDay() === day.index && day.index !== -1;
              });

              if (dayTasks.length === 0 && day.label !== 'Sin fecha') return null;
              if (dayTasks.length === 0 && day.label === 'Sin fecha' && tasks.every(t => t.fecha_entrega)) return null;

              return (
                <div key={day.label} className="space-y-4">
                  <div className="flex items-center gap-4 px-1">
                    <h2 className="text-sm font-bold uppercase tracking-[0.2em] text-muted-foreground/70">
                      {day.label}
                    </h2>
                    <div className="h-px flex-1 bg-border/50"></div>
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-muted rounded-full border shadow-sm">
                      {dayTasks.length}
                    </span>
                  </div>
                  
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {dayTasks.map((task) => (
                      <TaskCard key={task.id} task={task} showChecklist={true} />
                    ))}
                  </div>
                </div>
              );
            })}
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
            <AnimatePresence mode="popLayout">
              {columns.map((col) => (
                <section 
                  key={col} 
                  className={`space-y-6 p-4 rounded-2xl border transition-colors duration-200 min-h-[500px] ${getColColor(col)}`}
                  onDragOver={(e) => e.preventDefault()}
                  onDrop={(e) => handleDrop(e, col)}
                >
                  <div className="flex justify-between items-center px-1">
                    <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground/70">
                      {col.replace('_', ' ')}
                    </h2>
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-background rounded-full border shadow-sm">
                      {tasks.filter((t) => t.estado === col).length}
                    </span>
                  </div>
                  
                  <div className="space-y-4">
                    {tasks.filter((t) => t.estado === col).map((task) => (
                      <TaskCard key={task.id} task={task} />
                    ))}
                    {tasks.filter((t) => t.estado === col).length === 0 && (
                      <div className="border border-dashed border-border/50 rounded-xl h-24 flex items-center justify-center text-muted-foreground/40 text-xs font-medium">
                        Arrastra tareas aquí
                      </div>
                    )}
                  </div>
                </section>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>
    </main>
  );
}
