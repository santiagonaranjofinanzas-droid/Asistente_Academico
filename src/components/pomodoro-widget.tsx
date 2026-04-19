'use client';

import { useState, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Pause, Square, Timer, CheckCircle2 } from 'lucide-react';
import { Button } from './ui/button';
import { Card } from './ui/card';

const WORK_TIME = 25 * 60; // 25 minutes
const BREAK_TIME = 5 * 60; // 5 minutes

export function PomodoroWidget({ task, onClose }: { task?: any, onClose?: () => void }) {
  const [timeLeft, setTimeLeft] = useState(WORK_TIME);
  const [isActive, setIsActive] = useState(false);
  const [isBreak, setIsBreak] = useState(false);
  const [isMinimized, setIsMinimized] = useState(false);

  useEffect(() => {
    let interval: any = null;

    if (isActive && timeLeft > 0) {
      interval = setInterval(() => {
        setTimeLeft((time) => time - 1);
      }, 1000);
    } else if (timeLeft === 0) {
      // Timer finished
      if (!isBreak) {
        // Work finished, start break
        new Audio('https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg').play().catch(() => {});
        setIsBreak(true);
        setTimeLeft(BREAK_TIME);
        setIsActive(false);
      } else {
        // Break finished, reset
        new Audio('https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg').play().catch(() => {});
        setIsBreak(false);
        setTimeLeft(WORK_TIME);
        setIsActive(false);
      }
    }

    return () => clearInterval(interval);
  }, [isActive, timeLeft, isBreak]);

  const toggleTimer = () => setIsActive(!isActive);
  
  const resetTimer = () => {
    setIsActive(false);
    setIsBreak(false);
    setTimeLeft(WORK_TIME);
  };

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  const progress = isBreak 
    ? ((BREAK_TIME - timeLeft) / BREAK_TIME) * 100 
    : ((WORK_TIME - timeLeft) / WORK_TIME) * 100;

  if (!task && isMinimized) return null;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, y: 50, scale: 0.9 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        exit={{ opacity: 0, y: 50, scale: 0.9 }}
        className="fixed bottom-6 right-6 z-50 flex flex-col items-end gap-2"
      >
        <Card className="glass-card overflow-hidden border-primary/20 w-72 shadow-2xl">
          <div className={`h-1.5 w-full ${isBreak ? 'bg-green-500/20' : 'bg-primary/20'}`}>
            <motion.div 
              className={`h-full ${isBreak ? 'bg-green-500' : 'bg-primary'}`} 
              initial={{ width: 0 }}
              animate={{ width: `${progress}%` }}
              transition={{ duration: 1 }}
            />
          </div>
          
          <div className="p-4 flex flex-col items-center">
            <div className="w-full flex justify-between items-start mb-2">
              <span className={`text-xs font-bold uppercase tracking-wider ${isBreak ? 'text-green-500' : 'text-primary'}`}>
                {isBreak ? 'Descanso' : 'Enfoque'}
              </span>
              {onClose && (
                <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
                  &times;
                </button>
              )}
            </div>

            {task && (
              <p className="text-sm font-medium text-center line-clamp-1 mb-4 text-muted-foreground">
                {task.titulo}
              </p>
            )}

            <div className="text-5xl font-bold font-mono tracking-tighter mb-6 relative">
              {String(minutes).padStart(2, '0')}:{String(seconds).padStart(2, '0')}
              {isActive && (
                <motion.div
                  animate={{ opacity: [1, 0, 1] }}
                  transition={{ repeat: Infinity, duration: 2 }}
                  className="absolute -right-3 top-2 w-2 h-2 rounded-full bg-primary"
                />
              )}
            </div>

            <div className="flex items-center gap-3 w-full">
              <Button 
                variant={isActive ? "secondary" : "default"} 
                className={`flex-1 transition-all ${!isActive && !isBreak ? 'bg-primary text-primary-foreground hover:bg-primary/90' : ''} ${isBreak && !isActive ? 'bg-green-500 text-white hover:bg-green-600' : ''}`}
                onClick={toggleTimer}
              >
                {isActive ? <Pause className="w-4 h-4 mr-2" /> : <Play className="w-4 h-4 mr-2" />}
                {isActive ? 'Pausa' : 'Iniciar'}
              </Button>
              <Button variant="outline" size="icon" onClick={resetTimer}>
                <Square className="w-4 h-4" />
              </Button>
            </div>
          </div>
        </Card>
      </motion.div>
    </AnimatePresence>
  );
}
