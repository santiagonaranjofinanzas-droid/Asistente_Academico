'use client';

import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Play, Pause, RotateCcw, X, Target } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface PomodoroTimerProps {
  taskTitle: string;
  onClose: () => void;
}

export function PomodoroTimer({ taskTitle, onClose }: PomodoroTimerProps) {
  const [timeLeft, setTimeLeft] = useState(25 * 60); // 25 minutes in seconds
  const [isActive, setIsActive] = useState(false);
  const [isBreak, setIsBreak] = useState(false);
  const intervalRef = useRef<NodeJS.Timeout | null>(null);

  useEffect(() => {
    if (isActive && timeLeft > 0) {
      intervalRef.current = setInterval(() => {
        setTimeLeft((prev) => prev - 1);
      }, 1000);
    } else if (timeLeft === 0) {
      setIsActive(false);
      if (!isBreak) {
        // Switch to break
        setIsBreak(true);
        setTimeLeft(5 * 60); // 5 min break
      } else {
        // Switch to work
        setIsBreak(false);
        setTimeLeft(25 * 60);
      }
      // Play sound notification
      try {
        const audio = new Audio('/bell.mp3'); // Optional sound
        audio.play().catch(() => {});
      } catch (e) {}
    }

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [isActive, timeLeft, isBreak]);

  const toggleTimer = () => setIsActive(!isActive);

  const resetTimer = () => {
    setIsActive(false);
    setIsBreak(false);
    setTimeLeft(25 * 60);
  };

  const skipToNext = () => {
    setIsActive(false);
    if (!isBreak) {
      setIsBreak(true);
      setTimeLeft(5 * 60);
    } else {
      setIsBreak(false);
      setTimeLeft(25 * 60);
    }
  };

  const minutes = Math.floor(timeLeft / 60);
  const seconds = timeLeft % 60;
  
  // Calculate progress percentage
  const totalSeconds = isBreak ? 5 * 60 : 25 * 60;
  const progress = ((totalSeconds - timeLeft) / totalSeconds) * 100;

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0, scale: 0.95, y: 20 }}
        animate={{ opacity: 1, scale: 1, y: 0 }}
        exit={{ opacity: 0, scale: 0.95, y: 20 }}
        className="fixed bottom-6 right-6 z-50 w-80 bg-background/95 backdrop-blur-xl border border-border/50 shadow-2xl rounded-2xl overflow-hidden"
      >
        <div className="absolute top-0 left-0 w-full h-1 bg-muted">
          <div 
            className={`h-full transition-all duration-1000 ease-linear ${isBreak ? 'bg-green-500' : 'bg-primary'}`}
            style={{ width: `${progress}%` }}
          />
        </div>
        
        <div className="p-5">
          <div className="flex justify-between items-start mb-4">
            <div>
              <div className="flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-muted-foreground/70 mb-1">
                <Target className="w-3.5 h-3.5" />
                {isBreak ? 'Descanso Corto' : 'Modo Enfoque'}
              </div>
              <h3 className="font-semibold text-sm line-clamp-1 group-hover:text-primary transition-colors" title={taskTitle}>
                {taskTitle}
              </h3>
            </div>
            <button onClick={onClose} className="p-1.5 text-muted-foreground hover:bg-muted rounded-full transition-colors">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="flex flex-col items-center justify-center py-6">
            <div className={`text-6xl font-black tracking-tighter tabular-nums ${isBreak ? 'text-green-500' : 'text-primary'}`}>
              {minutes.toString().padStart(2, '0')}:{seconds.toString().padStart(2, '0')}
            </div>
          </div>

          <div className="flex justify-center gap-3">
            <Button
              variant="outline"
              size="icon"
              onClick={resetTimer}
              className="rounded-full w-10 h-10 border-border/50 hover:bg-muted"
            >
              <RotateCcw className="w-4 h-4" />
            </Button>
            
            <Button
              variant={isBreak ? "outline" : "default"}
              size="icon"
              onClick={toggleTimer}
              className={`rounded-full w-14 h-14 shadow-lg ${isBreak ? 'border-green-500/30 text-green-600 hover:bg-green-500/10 hover:text-green-700' : ''}`}
            >
              {isActive ? <Pause className="w-6 h-6" /> : <Play className="w-6 h-6 ml-1" />}
            </Button>
            
            <Button
              variant="outline"
              size="icon"
              onClick={skipToNext}
              className="rounded-full w-10 h-10 border-border/50 hover:bg-muted"
            >
              <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="w-4 h-4"><polygon points="5 4 15 12 5 20 5 4"/><line x1="19" y1="5" x2="19" y2="19"/></svg>
            </Button>
          </div>
        </div>
      </motion.div>
    </AnimatePresence>
  );
}
