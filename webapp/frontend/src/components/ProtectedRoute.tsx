import React from 'react';
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { UserRole, ProtectedRouteProps } from '../types/auth';
import { Loader2 } from 'lucide-react';

const ProtectedRoute: React.FC<ProtectedRouteProps> = ({ 
  children, 
  requiredRole,
  fallback 
}) => {
  const { isAuthenticated, isLoading, user } = useAuth();
  const location = useLocation();

  // Show loading spinner while checking authentication
  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <Loader2 className="h-8 w-8 animate-spin mx-auto mb-4" />
          <p className="text-gray-600">Loading...</p>
        </div>
      </div>
    );
  }

  // Redirect to login if not authenticated
  if (!isAuthenticated) {
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access if required role is specified
  if (requiredRole && user) {
    const hasRequiredRole = checkRoleAccess(user.role, requiredRole);
    
    if (!hasRequiredRole) {
      // Show fallback component or default unauthorized message
      return (
        fallback || (
          <div className="min-h-screen flex items-center justify-center">
            <div className="text-center">
              <h2 className="text-2xl font-bold text-gray-900 mb-2">Access Denied</h2>
              <p className="text-gray-600">
                You don't have permission to access this page.
              </p>
            </div>
          </div>
        )
      );
    }
  }

  // Render protected content
  return <>{children}</>;
};

// Helper function to check role hierarchy
function checkRoleAccess(userRole: UserRole, requiredRole: UserRole): boolean {
  const roleHierarchy = {
    [UserRole.VIEWER]: 0,
    [UserRole.USER]: 1,
    [UserRole.ADMIN]: 2,
  };

  return roleHierarchy[userRole] >= roleHierarchy[requiredRole];
}

export default ProtectedRoute;
