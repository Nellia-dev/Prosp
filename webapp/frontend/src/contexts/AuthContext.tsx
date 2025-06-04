import React, { createContext, useContext, useReducer, useEffect, ReactNode } from 'react';
import Cookies from 'js-cookie';
import { 
  AuthState, 
  AuthContextType, 
  LoginRequest, 
  RegisterRequest, 
  User,
  LoginResponse,
  mapApiRoleToUserRole 
} from '../types/auth';
import { apiClient, authApi } from '../services/api';

// Auth Actions
type AuthAction =
  | { type: 'LOGIN_START' }
  | { type: 'LOGIN_SUCCESS'; payload: { user: User; token: string } }
  | { type: 'LOGIN_FAILURE'; payload: string }
  | { type: 'LOGOUT' }
  | { type: 'REFRESH_TOKEN_SUCCESS'; payload: string }
  | { type: 'SET_LOADING'; payload: boolean }
  | { type: 'CLEAR_ERROR' }
  | { type: 'RESTORE_SESSION'; payload: { user: User; token: string } };

// Initial State
const initialState: AuthState = {
  user: null,
  token: null,
  isAuthenticated: false,
  isLoading: true, // Start with loading true to check for existing session
  error: null,
};

// Auth Reducer
function authReducer(state: AuthState, action: AuthAction): AuthState {
  switch (action.type) {
    case 'LOGIN_START':
      return {
        ...state,
        isLoading: true,
        error: null,
      };
    case 'LOGIN_SUCCESS':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      };
    case 'LOGIN_FAILURE':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: action.payload,
      };
    case 'LOGOUT':
      return {
        ...state,
        user: null,
        token: null,
        isAuthenticated: false,
        isLoading: false,
        error: null,
      };
    case 'REFRESH_TOKEN_SUCCESS':
      return {
        ...state,
        token: action.payload,
        isLoading: false,
        error: null,
      };
    case 'SET_LOADING':
      return {
        ...state,
        isLoading: action.payload,
      };
    case 'CLEAR_ERROR':
      return {
        ...state,
        error: null,
      };
    case 'RESTORE_SESSION':
      return {
        ...state,
        user: action.payload.user,
        token: action.payload.token,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      };
    default:
      return state;
  }
}

// Create Context
const AuthContext = createContext<AuthContextType | undefined>(undefined);

// Token Storage Keys
const TOKEN_KEY = 'nellia_access_token';
const REFRESH_TOKEN_KEY = 'nellia_refresh_token';
const USER_KEY = 'nellia_user';

// Auth Provider
interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [state, dispatch] = useReducer(authReducer, initialState);

  // Check for existing session on mount
  useEffect(() => {
    const checkExistingSession = () => {
      try {
        const token = Cookies.get(TOKEN_KEY);
        const userStr = Cookies.get(USER_KEY);
        
        if (token && userStr) {
          const user = JSON.parse(userStr);
          
          // Set token in API client
          apiClient.setAuthToken(token);
          
          dispatch({
            type: 'RESTORE_SESSION',
            payload: { user, token }
          });
        } else {
          dispatch({ type: 'SET_LOADING', payload: false });
        }
      } catch (error) {
        console.error('Error restoring session:', error);
        // Clear potentially corrupted data
        clearStoredAuth();
        dispatch({ type: 'SET_LOADING', payload: false });
      }
    };

    checkExistingSession();
  }, []);

  // Helper function to store auth data
  const storeAuthData = (loginResponse: LoginResponse) => {
    const { access_token, refresh_token, user, expires_in } = loginResponse;
    
    // Calculate expiry date (convert seconds to days for cookie expiry)
    // Default to 24 hours if expires_in is not provided
    const expiryDays = expires_in ? expires_in / (24 * 60 * 60) : 1;
    
    // Store in cookies
    Cookies.set(TOKEN_KEY, access_token, { expires: expiryDays, secure: true, sameSite: 'strict' });
    if (refresh_token) {
      Cookies.set(REFRESH_TOKEN_KEY, refresh_token, { expires: expiryDays * 2, secure: true, sameSite: 'strict' });
    }
    Cookies.set(USER_KEY, JSON.stringify(user), { expires: expiryDays, secure: true, sameSite: 'strict' });
    
    // Set token in API client
    apiClient.setAuthToken(access_token);
  };

  // Helper function to clear stored auth data
  const clearStoredAuth = () => {
    Cookies.remove(TOKEN_KEY);
    Cookies.remove(REFRESH_TOKEN_KEY);
    Cookies.remove(USER_KEY);
    apiClient.setAuthToken(null);
  };

  // Login function
  const login = async (credentials: LoginRequest): Promise<void> => {
    dispatch({ type: 'LOGIN_START' });
    
    try {
      const apiResponse = await authApi.login(credentials);
      
      // Map API response to auth types
      const loginData: LoginResponse = {
        access_token: apiResponse.access_token,
        refresh_token: undefined, // API doesn't provide refresh token yet
        expires_in: undefined, // API doesn't provide expires_in yet
        user: {
          id: apiResponse.user.id,
          email: apiResponse.user.email,
          name: undefined, // API doesn't provide name yet
          role: mapApiRoleToUserRole(apiResponse.user.role),
          createdAt: apiResponse.user.createdAt,
          updatedAt: apiResponse.user.updatedAt
        }
      };
      
      // Store auth data
      storeAuthData(loginData);
      
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          user: loginData.user,
          token: loginData.access_token
        }
      });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { data?: { message?: string } } }).response?.data?.message || 'Login failed. Please check your credentials.'
        : 'Login failed. Please check your credentials.';
      dispatch({
        type: 'LOGIN_FAILURE',
        payload: errorMessage
      });
      throw error;
    }
  };

  // Register function
  const register = async (userData: RegisterRequest): Promise<void> => {
    dispatch({ type: 'LOGIN_START' });
    
    try {
      const apiResponse = await authApi.register(userData);
      
      // Map API response to auth types
      const loginData: LoginResponse = {
        access_token: apiResponse.access_token,
        refresh_token: undefined, // API doesn't provide refresh token yet
        expires_in: undefined, // API doesn't provide expires_in yet
        user: {
          id: apiResponse.user.id,
          email: apiResponse.user.email,
          name: userData.name, // Use the name from registration
          role: mapApiRoleToUserRole(apiResponse.user.role),
          createdAt: apiResponse.user.createdAt,
          updatedAt: apiResponse.user.updatedAt
        }
      };
      
      // Store auth data
      storeAuthData(loginData);
      
      dispatch({
        type: 'LOGIN_SUCCESS',
        payload: {
          user: loginData.user,
          token: loginData.access_token
        }
      });
    } catch (error: unknown) {
      const errorMessage = error instanceof Error && 'response' in error 
        ? (error as { response?: { data?: { message?: string } } }).response?.data?.message || 'Registration failed. Please try again.'
        : 'Registration failed. Please try again.';
      dispatch({
        type: 'LOGIN_FAILURE',
        payload: errorMessage
      });
      throw error;
    }
  };

  // Logout function
  const logout = () => {
    clearStoredAuth();
    dispatch({ type: 'LOGOUT' });
  };

  // Refresh token function
  const refreshToken = async (): Promise<void> => {
    try {
      const refreshTokenValue = Cookies.get(REFRESH_TOKEN_KEY);
      
      if (!refreshTokenValue) {
        throw new Error('No refresh token available');
      }

      const response = await apiClient.post<{ access_token: string; expires_in: number }>('/auth/refresh', {
        refresh_token: refreshTokenValue
      });
      
      const { access_token, expires_in } = response.data;
      
      // Update stored token
      const expiryDays = expires_in / (24 * 60 * 60);
      Cookies.set(TOKEN_KEY, access_token, { expires: expiryDays, secure: true, sameSite: 'strict' });
      
      // Set token in API client
      apiClient.setAuthToken(access_token);
      
      dispatch({
        type: 'REFRESH_TOKEN_SUCCESS',
        payload: access_token
      });
    } catch (error) {
      console.error('Token refresh failed:', error);
      // If refresh fails, logout user
      logout();
      throw error;
    }
  };

  // Clear error function
  const clearError = () => {
    dispatch({ type: 'CLEAR_ERROR' });
  };

  const contextValue: AuthContextType = {
    ...state,
    login,
    register,
    logout,
    refreshToken,
    clearError,
  };

  return (
    <AuthContext.Provider value={contextValue}>
      {children}
    </AuthContext.Provider>
  );
};

// Custom hook to use auth context
export const useAuth = (): AuthContextType => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export default AuthContext;
