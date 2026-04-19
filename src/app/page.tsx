'use client';

import { useEffect, useState } from 'react';
import { supabase } from '@/lib/supabase';
import { TaskCard } from '@/components/task-card';
import { Button } from '@/components/ui/button';
import { LayoutGrid, List, Sparkles, Filter } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

export default function Dashboard() {
  const [tasks, setTasks] = useState<any[]>([]);
  const [view, setView] = useState<'kanban' | 'list'>('kanban');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchTasks();

    // Subscribe to Realtime changes
    const channel = supabase
      .channel('tasks_channel')
      .on(
        'postgres_changes',
        { event: '*', table: 'tareas' },
        (payload) => {
          console.log('Change received!', payload);
          if (payload.eventType === 'INSERT') {
            setTasks((prev) => [payload.new, ...prev]);
          } else if (payload.eventType === 'UPDATE') {
            setTasks((prev) => prev.map((t) => (t.id === payload.new.id ? payload.new : t)));
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
    const { data, error } = await supabase
      .from('tareas')
      .select('*')
      .eq('archivada', false)
      .order('creado_at', { ascending: false });

    if (data) setTasks(data);
    setLoading(false);
  }

  const columns = ['por_empezar', 'en_proceso', 'lista'];

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
          </div>
        </header>

        {/* Dashboard Content */}
        {loading ? (
          <div className="flex items-center justify-center h-64 opacity-50">
            <p className="animate-pulse font-medium">Cargando tareas...</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 items-start">
            <AnimatePresence mode="popLayout">
              {columns.map((col) => (
                <section key={col} className="space-y-6">
                  <div className="flex justify-between items-center px-2">
                    <h2 className="text-xs font-bold uppercase tracking-[0.2em] text-muted-foreground/70">
                      {col.replace('_', ' ')}
                    </h2>
                    <span className="text-[10px] font-bold px-2 py-0.5 bg-muted rounded-full">
                      {tasks.filter((t) => t.estado === col).length}
                    </span>
                  </div>
                  
                  <div className="space-y-4">
                    {tasks.filter((t) => t.estado === col).map((task) => (
                      <TaskCard key={task.id} task={task} />
                    ))}
                    {tasks.filter((t) => t.estado === col).length === 0 && (
                      <div className="border border-dashed rounded-xl h-24 flex items-center justify-center text-muted-foreground/30 text-xs">
                        No hay tareas
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
