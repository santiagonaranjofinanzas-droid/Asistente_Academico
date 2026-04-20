'use client';

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, CheckCircle2, Clock, MoreVertical, Timer, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { formatDistanceToNow, isPast, isToday, isTomorrow, differenceInDays, format } from 'date-fns';
import { es } from 'date-fns/locale';

interface Task {
  id: string;
  materia: string;
  titulo: string;
  descripcion: string;
  fecha_entrega: string;
  estado: string;
}

const statusColors = {
  por_empezar: 'bg-slate-500/10 text-slate-500 border-slate-500/20',
  en_proceso: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  lista: 'bg-green-500/10 text-green-500 border-green-500/20',
  entregada: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
};

export function TaskCard({ task, onFocus }: { task: Task, onFocus?: () => void }) {
  return (
    <motion.div
      draggable={true}
      onDragStart={(e: React.DragEvent) => {
        e.dataTransfer.setData('taskId', task.id);
      }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -2 }}
      className="group cursor-grab active:cursor-grabbing"
    >
      <Card className="glass-card overflow-hidden">
        <CardHeader className="p-4 pb-2">
          <div className="flex justify-between items-start">
            <Badge variant="outline" className="text-[10px] uppercase tracking-wider font-semibold opacity-70">
              {task.materia}
            </Badge>
            <div className={`text-[10px] px-2 py-0.5 rounded-full border ${statusColors[task.estado as keyof typeof statusColors]}`}>
              {task.estado.replace('_', ' ')}
            </div>
          </div>
          <CardTitle className="text-base font-bold mt-2 group-hover:text-primary transition-colors">
            {task.titulo}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-4 pt-0">
          <p className="text-xs text-muted-foreground line-clamp-2 mb-4">
            {task.descripcion || 'Sin descripción adicional.'}
          </p>
          <div className="flex items-center gap-4 text-[11px] font-medium">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Calendar className="w-3.5 h-3.5" />
              <span>{task.fecha_entrega ? format(new Date(task.fecha_entrega), 'd MMM', { locale: es }) : 'Sin fecha'}</span>
            </div>
            
            {task.fecha_entrega && (
              <div className={`flex items-center gap-1.5 ${isPast(new Date(task.fecha_entrega)) && !isToday(new Date(task.fecha_entrega)) ? 'text-destructive' : 'text-muted-foreground'}`}>
                {isPast(new Date(task.fecha_entrega)) && !isToday(new Date(task.fecha_entrega)) ? (
                  <AlertCircle className="w-3.5 h-3.5" />
                ) : (
                  <Clock className="w-3.5 h-3.5" />
                )}
                <span>
                  {isToday(new Date(task.fecha_entrega)) ? 'Vence hoy' : 
                   isTomorrow(new Date(task.fecha_entrega)) ? 'Mañana' :
                   isPast(new Date(task.fecha_entrega)) ? 'Vencida' :
                   `Faltan ${differenceInDays(new Date(task.fecha_entrega), new Date())}d`}
                </span>
              </div>
            )}
          </div>
          {onFocus && task.estado !== 'lista' && (
            <div className="mt-4 pt-3 border-t border-border/50">
              <Button 
                variant="ghost" 
                size="sm" 
                className="w-full h-7 text-xs text-muted-foreground hover:text-primary hover:bg-primary/10"
                onClick={(e) => {
                  e.stopPropagation();
                  onFocus();
                }}
              >
                <Timer className="w-3.5 h-3.5 mr-2" />
                Iniciar Pomodoro
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </motion.div>
  );
}
