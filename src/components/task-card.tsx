'use client';

import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Calendar, CheckCircle2, Clock, MoreVertical, Timer, AlertCircle } from 'lucide-react';
import { motion } from 'framer-motion';
import { formatDistanceToNow, isPast, isToday, isTomorrow, differenceInDays, format } from 'date-fns';
import { es } from 'date-fns/locale';

interface Attachment {
  nombre: string;
  url: string;
}

interface Task {
  id: string;
  materia: string;
  titulo: string;
  descripcion: string;
  fecha_entrega: string;
  estado: string;
  texto_extraido?: string;
  archivos_adjuntos?: Attachment[] | string;
  resumen_ia?: string;
  checklist?: { id: string; text: string; completed: boolean }[];
}

const statusColors = {
  por_empezar: 'bg-slate-500/10 text-slate-500 border-slate-500/20',
  en_proceso: 'bg-blue-500/10 text-blue-500 border-blue-500/20',
  lista: 'bg-green-500/10 text-green-500 border-green-500/20',
  entregada: 'bg-purple-500/10 text-purple-500 border-purple-500/20',
};

import { Sparkles as SparklesIcon, Loader2, Download as DownloadIcon, FileText, Brain, Plus, Trash2, CheckCircle, Play } from 'lucide-react';
import { useState, useMemo } from 'react';
import { Checkbox } from '@/components/ui/checkbox';
import { supabase } from '@/lib/supabase';
import { PomodoroTimer } from '@/components/pomodoro-timer';

export function TaskCard({ task, showChecklist = false }: { task: Task, showChecklist?: boolean }) {
  const [showSummary, setShowSummary] = useState(false);
  const [showExtracted, setShowExtracted] = useState(false);
  const [newItemText, setNewItemText] = useState('');
  const [isUpdating, setIsUpdating] = useState(false);
  const [showPomodoro, setShowPomodoro] = useState(false);

  // Initialize checklist from task or empty array
  const checklist = useMemo(() => {
    if (!task.checklist) return [];
    if (Array.isArray(task.checklist)) return task.checklist;
    if (typeof task.checklist === 'string') {
      try {
        return JSON.parse(task.checklist);
      } catch {
        return [];
      }
    }
    return [];
  }, [task.checklist]);

  const handleAddItem = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newItemText.trim()) return;

    const newItem = {
      id: crypto.randomUUID(),
      text: newItemText.trim(),
      completed: false
    };

    const updatedChecklist = [...checklist, newItem];
    
    // Update Supabase
    const { error } = await supabase
      .from('tareas')
      .update({ checklist: updatedChecklist })
      .eq('id', task.id);

    if (!error) {
      setNewItemText('');
    }
  };

  const handleToggleItem = async (itemId: string) => {
    const updatedChecklist = checklist.map((item: any) => 
      item.id === itemId ? { ...item, completed: !item.completed } : item
    );

    const wasCompleted = updatedChecklist.find((i: any) => i.id === itemId)?.completed;
    
    let updatedEstado = task.estado;
    // Auto move to "en_proceso" if a check is marked and it was "por_empezar"
    if (wasCompleted && task.estado === 'por_empezar') {
      updatedEstado = 'en_proceso';
    }

    const { error } = await supabase
      .from('tareas')
      .update({ 
        checklist: updatedChecklist,
        estado: updatedEstado
      })
      .eq('id', task.id);
  };

  const handleDeleteItem = async (itemId: string) => {
    const updatedChecklist = checklist.filter((item: any) => item.id !== itemId);
    
    await supabase
      .from('tareas')
      .update({ checklist: updatedChecklist })
      .eq('id', task.id);
  };

  // Parse archivos_adjuntos which may be a JSON string or already an array
  const attachments: Attachment[] = useMemo(() => {
    if (!task.archivos_adjuntos) return [];
    if (typeof task.archivos_adjuntos === 'string') {
      try {
        const parsed = JSON.parse(task.archivos_adjuntos);
        return Array.isArray(parsed) ? parsed : [];
      } catch {
        return [];
      }
    }
    return Array.isArray(task.archivos_adjuntos) ? task.archivos_adjuntos : [];
  }, [task.archivos_adjuntos]);

  const hasSummary = !!task.resumen_ia;
  const hasExtractedText = !!task.texto_extraido && task.texto_extraido.trim().length > 0;

  const isReadyToSubmit = useMemo(() => {
    if (task.estado === 'entregada' || task.estado === 'lista') return false;
    if (!checklist || checklist.length === 0) return false;
    
    const uncompleted = checklist.filter((item: any) => !item.completed);
    if (uncompleted.length === 1) {
      const text = uncompleted[0].text.trim().toLowerCase();
      const keywords = ['enviar', 'subir', 'entregar', 'subir trabajo', 'subir tarea', 'finalizar'];
      return keywords.some(kw => text.includes(kw));
    }
    return false;
  }, [checklist, task.estado]);

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, scale: 0.95 }}
      whileHover={{ y: -2 }}
    >
      <div
        draggable={true}
        onDragStart={(e: React.DragEvent) => {
          e.dataTransfer.setData('taskId', task.id);
        }}
        className="group cursor-grab active:cursor-grabbing h-full"
      >
        <Card className={`glass-card overflow-hidden transition-all duration-500 h-full ${isReadyToSubmit ? '!bg-emerald-500/20 border-emerald-500/40 dark:!bg-emerald-500/10' : ''}`}>
        <CardHeader className="p-3 sm:p-4 pb-2">
          <div className="flex justify-between items-start gap-2">
            <div className="flex flex-col gap-1">
              <Badge variant="outline" className="text-[9px] sm:text-[10px] uppercase tracking-wider font-semibold opacity-70 truncate px-1.5 py-0 w-fit">
                {task.materia}
              </Badge>
              {isReadyToSubmit && (
                <Badge className="bg-emerald-500/20 text-emerald-600 dark:text-emerald-400 border-emerald-500/30 text-[8px] uppercase py-0 px-1.5 animate-pulse">
                  Listo para enviar
                </Badge>
              )}
            </div>
            <div className="flex items-center gap-1.5 shrink-0">
              <div className={`text-[9px] sm:text-[10px] px-2 py-0.5 rounded-full border ${statusColors[task.estado as keyof typeof statusColors]}`}>
                {task.estado.replace('_', ' ')}
              </div>
              {task.estado === 'en_proceso' && (
                <Button 
                  variant="ghost" 
                  size="icon" 
                  className="h-6 w-6 text-blue-500 hover:text-blue-600 hover:bg-blue-500/10 rounded-full"
                  onClick={(e) => { e.stopPropagation(); setShowPomodoro(true); }}
                  title="Modo Enfoque"
                >
                  <Play className="w-3.5 h-3.5 fill-current" />
                </Button>
              )}
            </div>
          </div>
          <CardTitle className="text-sm sm:text-base font-bold mt-2 group-hover:text-primary transition-colors line-clamp-2 leading-tight">
            {task.titulo}
          </CardTitle>
        </CardHeader>
        <CardContent className="p-3 sm:p-4 pt-0">
          <p className="text-[11px] sm:text-xs text-muted-foreground line-clamp-2 mb-3 sm:mb-4">
            {task.descripcion || 'Sin descripción adicional.'}
          </p>
          <div className="flex items-center gap-3 sm:gap-4 text-[10px] sm:text-[11px] font-medium border-b border-border/50 pb-3 mb-3">
            <div className="flex items-center gap-1.5 text-muted-foreground">
              <Calendar className="w-3 sm:w-3.5 h-3 sm:h-3.5" />
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
          
          {/* Attachments Section */}
          {attachments.length > 0 && (
            <div className="flex flex-col gap-1.5 mb-3">
              <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider font-semibold">
                📎 Archivos ({attachments.length})
              </span>
              {attachments.map((archivo, i) => (
                <a 
                  key={i} 
                  href={archivo.url} 
                  target="_blank" 
                  rel="noopener noreferrer"
                  onClick={(e) => e.stopPropagation()}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-md bg-primary/5 border border-primary/10 hover:bg-primary/10 hover:border-primary/20 transition-all text-[11px] text-foreground/80 w-fit max-w-full overflow-hidden group/link"
                >
                  <DownloadIcon className="w-3 h-3 flex-shrink-0 text-primary group-hover/link:scale-110 transition-transform" />
                  <span className="truncate font-medium">{archivo.nombre}</span>
                </a>
              ))}
            </div>
          )}
          
          {/* AI Summary Button - reads pre-computed summary from DB */}
          {hasSummary && (
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={(e) => { e.stopPropagation(); setShowSummary(!showSummary); }}
              className="w-full h-7 text-xs text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
            >
              <Brain className="w-3.5 h-3.5 mr-2 text-primary" />
              {showSummary ? 'Cerrar Resumen IA' : 'Ver Resumen IA'}
            </Button>
          )}
          
          {/* Extracted Text Toggle */}
          {hasExtractedText && !hasSummary && (
            <Button 
              variant="ghost" 
              size="sm" 
              onClick={(e) => { e.stopPropagation(); setShowExtracted(!showExtracted); }}
              className="w-full h-7 text-xs text-muted-foreground hover:text-primary hover:bg-primary/10 transition-colors"
            >
              <FileText className="w-3.5 h-3.5 mr-2 text-primary" />
              {showExtracted ? 'Cerrar Texto' : 'Ver Texto Extraído'}
            </Button>
          )}

          {/* No AI indicator when summary is pending */}
          {!hasSummary && !hasExtractedText && task.estado !== 'entregada' && (
            <div className="w-full h-7 flex items-center justify-center text-[10px] text-muted-foreground/40">
              <SparklesIcon className="w-3 h-3 mr-1.5 opacity-40" />
              Resumen IA pendiente
            </div>
          )}

          {/* AI Summary Panel */}
          {showSummary && task.resumen_ia && (
            <motion.div 
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              className="mt-3 p-3 rounded-lg bg-primary/5 border border-primary/20 text-xs text-muted-foreground whitespace-pre-wrap select-text cursor-text"
              onPointerDown={(e) => e.stopPropagation()}
            >
               {task.resumen_ia}
            </motion.div>
          )}

          {/* Extracted Text Panel */}
          {showExtracted && task.texto_extraido && (
            <motion.div 
              initial={{ height: 0, opacity: 0 }}
              animate={{ height: 'auto', opacity: 1 }}
              className="mt-3 p-3 rounded-lg bg-muted/30 border text-xs text-muted-foreground whitespace-pre-wrap select-text cursor-text max-h-48 overflow-y-auto"
              onPointerDown={(e) => e.stopPropagation()}
            >
               {task.texto_extraido}
            </motion.div>
          )}

          {/* Checklist Section */}
          {showChecklist && (
            <div className="mt-6 space-y-3 pt-4 border-t border-border/50">
              <div className="flex flex-col gap-2">
                <div className="flex items-center justify-between">
                  <span className="text-[10px] text-muted-foreground/60 uppercase tracking-wider font-semibold flex items-center gap-1.5">
                    <CheckCircle className="w-3 h-3" />
                    Checklist ({checklist.filter((i: any) => i.completed).length}/{checklist.length})
                  </span>
                </div>
                
                {checklist.length > 0 && (
                  <div className="h-1.5 w-full bg-muted/50 rounded-full overflow-hidden border border-border/50">
                    <div 
                      className="h-full bg-primary/80 transition-all duration-500 ease-out"
                      style={{ width: `${(checklist.filter((i: any) => i.completed).length / checklist.length) * 100}%` }}
                    />
                  </div>
                )}
              </div>

              <div className="space-y-2 mt-2">
                {checklist.map((item: any) => (
                  <div key={item.id} className="flex items-center gap-2 group/item">
                    <Checkbox 
                      id={item.id} 
                      checked={item.completed}
                      onCheckedChange={() => handleToggleItem(item.id)}
                      className="w-3.5 h-3.5"
                    />
                    <label 
                      htmlFor={item.id}
                      className={`text-[11px] flex-1 cursor-pointer transition-colors ${item.completed ? 'text-muted-foreground/50 line-through' : 'text-foreground/80'}`}
                    >
                      {item.text}
                    </label>
                    <button 
                      onClick={() => handleDeleteItem(item.id)}
                      className="opacity-0 group-hover/item:opacity-100 p-1 hover:text-destructive transition-all"
                    >
                      <Trash2 className="w-3 h-3" />
                    </button>
                  </div>
                ))}
              </div>

              <form onSubmit={handleAddItem} className="flex gap-2 mt-2">
                <input
                  type="text"
                  placeholder="Añadir ítem..."
                  value={newItemText}
                  onChange={(e) => setNewItemText(e.target.value)}
                  className="flex-1 bg-muted/30 border-none rounded-md px-2 py-1 text-[11px] focus:ring-1 focus:ring-primary/30 outline-none"
                  onClick={(e) => e.stopPropagation()}
                />
                <Button type="submit" size="icon" variant="ghost" className="h-6 w-6">
                  <Plus className="w-3 h-3" />
                </Button>
              </form>
            </div>
          )}
        </CardContent>
      </Card>
      </div>

      {showPomodoro && (
        <PomodoroTimer 
          taskTitle={task.titulo} 
          onClose={() => setShowPomodoro(false)} 
        />
      )}
    </motion.div>
  );
}
