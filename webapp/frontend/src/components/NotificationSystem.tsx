import React from 'react';
import { useToast } from '../hooks/use-toast';
import { Toaster } from './ui/toaster';

export interface NotificationProps {
  title: string;
  message: string;
  type?: 'default' | 'success' | 'warning' | 'error';
  duration?: number;
}

export const NotificationSystem: React.FC = () => {
  return <Toaster />;
};

export const useNotifications = () => {
  const { toast } = useToast();

  const showNotification = ({ title, message, type = 'default', duration = 5000 }: NotificationProps) => {
    toast({
      title,
      description: message,
      variant: type === 'error' ? 'destructive' : 'default',
      duration,
    });
  };

  const showSuccess = (title: string, message: string) => {
    showNotification({ title, message, type: 'success' });
  };

  const showError = (title: string, message: string) => {
    showNotification({ title, message, type: 'error' });
  };

  const showWarning = (title: string, message: string) => {
    showNotification({ title, message, type: 'warning' });
  };

  const showInfo = (title: string, message: string) => {
    showNotification({ title, message, type: 'default' });
  };

  return {
    showNotification,
    showSuccess,
    showError,
    showWarning,
    showInfo,
  };
};

export default NotificationSystem;
