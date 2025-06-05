import { useConnectionStatus, useNelliaSocket } from '../hooks/useSocketIO';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Wifi, WifiOff, RotateCcw, AlertCircle } from 'lucide-react';

interface ConnectionStatusProps {
  className?: string;
  showText?: boolean;
}

export const ConnectionStatus = ({ className = '', showText = true }: ConnectionStatusProps) => {
  const { status, statusColor, statusText, isConnected } = useConnectionStatus();
  const { connect } = useNelliaSocket();

  const getStatusIcon = () => {
    switch (status) {
      case 'connected':
        return <Wifi className="w-3 h-3" />;
      case 'connecting':
        return <RotateCcw className="w-3 h-3 animate-spin" />;
      case 'error':
        return <AlertCircle className="w-3 h-3" />;
      default:
        return <WifiOff className="w-3 h-3" />;
    }
  };

  const getStatusBadgeColor = () => {
    switch (status) {
      case 'connected':
        return 'bg-green-500 hover:bg-green-600';
      case 'connecting':
        return 'bg-yellow-500 hover:bg-yellow-600';
      case 'error':
        return 'bg-red-500 hover:bg-red-600';
      default:
        return 'bg-gray-500 hover:bg-gray-600';
    }
  };

  const handleReconnect = () => {
    if (!isConnected) {
      connect();
    }
  };

  if (status === 'connecting') {
    return (
      <Badge className={`${getStatusBadgeColor()} text-white ${className}`}>
        {getStatusIcon()}
        {showText && <span className="ml-1">{statusText}</span>}
      </Badge>
    );
  }

  if (status === 'error' || status === 'disconnected') {
    return (
      <Button
        onClick={handleReconnect}
        size="sm"
        variant="outline"
        className={`border-red-500 text-red-500 hover:bg-red-500 hover:text-white ${className}`}
      >
        {getStatusIcon()}
        {showText && <span className="ml-1">{statusText}</span>}
      </Button>
    );
  }

  return (
    <Badge className={`${getStatusBadgeColor()} text-white ${className}`}>
      {getStatusIcon()}
      {showText && <span className="ml-1">{statusText}</span>}
    </Badge>
  );
};

export default ConnectionStatus;
