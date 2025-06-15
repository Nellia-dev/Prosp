import { useWebSocket } from '../contexts/WebSocketContext';
import { Badge } from './ui/badge';
import { Button } from './ui/button';
import { Wifi, WifiOff, RotateCcw, AlertCircle } from 'lucide-react';

interface ConnectionStatusProps {
  className?: string;
  showText?: boolean;
}

export const ConnectionStatus = ({ className = '', showText = true }: ConnectionStatusProps) => {
  const { connectionStatus, isConnected, connect } = useWebSocket();

  const getStatusIcon = () => {
    switch (connectionStatus) {
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
    switch (connectionStatus) {
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
  
  const statusText = {
    connected: 'Connected',
    connecting: 'Connecting...',
    error: 'Connection Error',
    disconnected: 'Disconnected',
  }[connectionStatus];


  const handleReconnect = () => {
    if (!isConnected) {
      connect();
    }
  };

  if (connectionStatus === 'connecting') {
    return (
      <Badge className={`${getStatusBadgeColor()} text-white ${className}`}>
        {getStatusIcon()}
        {showText && <span className="ml-1">{statusText}</span>}
      </Badge>
    );
  }

  if (connectionStatus === 'error' || connectionStatus === 'disconnected') {
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
