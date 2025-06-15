import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { 
  Wifi, 
  WifiOff, 
  Loader2, 
  AlertTriangle,
  RefreshCw 
} from "lucide-react";
import { useWebSocket } from "../contexts/WebSocketContext";

interface ConnectionStatusIndicatorProps {
  showText?: boolean;
  compact?: boolean;
}

export const ConnectionStatusIndicator = ({
  showText = true,
  compact = false
}: ConnectionStatusIndicatorProps) => {
  const { connectionStatus, isConnected, connect } = useWebSocket();

  const statusText = {
    connecting: 'Connecting...',
    connected: 'Connected',
    disconnected: 'Disconnected',
    error: 'Error',
  }[connectionStatus];

  const statusColor = {
    connecting: 'text-yellow-400',
    connected: 'text-green-400',
    disconnected: 'text-gray-400',
    error: 'text-red-400',
  }[connectionStatus];

  const getIcon = () => {
    switch (connectionStatus) {
      case 'connected':
        return <Wifi className="w-3 h-3" />;
      case 'connecting':
        return <Loader2 className="w-3 h-3 animate-spin" />;
      case 'error':
        return <AlertTriangle className="w-3 h-3" />;
      default:
        return <WifiOff className="w-3 h-3" />;
    }
  };

  const getBadgeVariant = () => {
    switch (connectionStatus) {
      case 'connected':
        return 'default';
      case 'connecting':
        return 'secondary';
      case 'error':
        return 'destructive';
      default:
        return 'outline';
    }
  };

  if (compact) {
    return (
      <div className="flex items-center space-x-1">
        <div className={statusColor}>
          {getIcon()}
        </div>
        {connectionStatus === 'error' && (
          <Button
            size="sm"
            variant="ghost"
            onClick={connect}
            className="h-6 w-6 p-0"
          >
            <RefreshCw className="w-3 h-3" />
          </Button>
        )}
      </div>
    );
  }

  return (
    <div className="flex items-center space-x-2">
      <Badge
        variant={getBadgeVariant()}
        className={`text-xs ${statusColor} border-current`}
      >
        {getIcon()}
        {showText && (
          <span className="ml-1">{statusText}</span>
        )}
      </Badge>
      
      {connectionStatus === 'error' && (
        <Button
          size="sm"
          variant="outline"
          onClick={connect}
          className="h-6 px-2 text-xs"
        >
          <RefreshCw className="w-3 h-3 mr-1" />
          Retry
        </Button>
      )}
    </div>
  );
};
