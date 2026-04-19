'use client';

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Calendar, CheckCircle2, Clock, MoreVertical } from 'lucide-react';
import { motion } from 'framer-motion';

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

export function TaskCard({ task }: { task: Task }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -2 }}
      className="group"
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
          <div className="flex items-center gap-4 text-[11px] text-muted-foreground font-medium">
            <div className="flex items-center gap-1.5">
              <Calendar className="w-3.5 h-3.5" />
              <span>{new Date(task.fecha_entrega || Date.now()).toLocaleDateString('es-ES', { month: 'short', day: 'numeric' })}</span>
            </div>
            <div className="flex items-center gap-1.5">
              <Clock className="w-3.5 h-3.5" />
              <span>Restante: 2d</span>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
