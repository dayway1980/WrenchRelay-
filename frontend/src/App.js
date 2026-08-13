import { useEffect } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import ErrorBoundary from "@/components/ErrorBoundary";
import LegalPage from "@/pages/LegalPage";
import AssetsPage from "@/pages/AssetsPage";
import AssetDetailPage from "@/pages/AssetDetailPage";
import AuthPage from "@/pages/AuthPage";
import ProductionAuthPage from "@/pages/ProductionAuthPage";
import GoogleAuthCallback from "@/pages/GoogleAuthCallback";
import DashboardPage from "@/pages/DashboardPage";
import MarketingPage from "@/pages/MarketingPage";
import LandingPage from "@/pages/LandingPage";
import RepositionedLandingPage from "@/pages/RepositionedLandingPage";
import OnboardingPage from "@/pages/OnboardingPage";
import CmmsConnectPage from "@/pages/CmmsConnectPage";
import SettingsPage from "@/pages/SettingsPage";
import WorkOrderDetailPage from "@/pages/WorkOrderDetailPage";
import WorkOrdersPage from "@/pages/WorkOrdersPage";
import ProductionWorkOrdersPage from "@/pages/ProductionWorkOrdersPage";
import ProductionWorkOrderDetailPage from "@/pages/ProductionWorkOrderDetailPage";
import VoicePage from "@/pages/VoicePage";
import ConversationPage from "@/pages/ConversationPage";
import TechnicianConsolePage from "@/pages/TechnicianConsolePage";
import BillingPage from "@/pages/BillingPage";
import NewWorkOrderPage from "@/pages/NewWorkOrderPage";
import "@/App.css";

function ProtectedRoute({ children }) {
  const { session, loading } = useAuth();
  if (loading) return <div className="route-loading" data-testid="session-loading">Checking your workspace…</div>;
  return session ? children : <Navigate to="/login" replace />;
}

function ApplicationRoutes() {
  if (window.location.hash?.includes("session_id=")) return <GoogleAuthCallback />;
  return <Routes>
    <Route path="/" element={<RepositionedLandingPage />} />
    <Route path="/landing" element={<LandingPage />} />
    <Route path="/product" element={<MarketingPage />} />
    <Route path="/how-it-works" element={<MarketingPage />} />
    <Route path="/parts-kitting" element={<MarketingPage />} />
    <Route path="/relay-mentor" element={<MarketingPage />} />
    <Route path="/integrations" element={<MarketingPage />} />
    <Route path="/pricing" element={<MarketingPage />} />
    <Route path="/security" element={<MarketingPage />} />
    <Route path="/contact" element={<MarketingPage />} />
    <Route path="/demo" element={<MarketingPage />} />
    <Route path="/privacy" element={<LegalPage />} />
    <Route path="/terms" element={<LegalPage />} />
    <Route path="/support" element={<LegalPage />} />
    <Route path="/data-deletion" element={<LegalPage />} />
    <Route path="/safety" element={<MarketingPage />} />
    <Route path="/faq" element={<MarketingPage />} />
    <Route path="/login" element={<ProductionAuthPage />} />
    <Route path="/signup" element={<ProductionAuthPage register />} />
    <Route path="/register" element={<ProductionAuthPage register />} />
    <Route path="/app" element={<ProtectedRoute><TechnicianConsolePage /></ProtectedRoute>} />
    <Route path="/app/conversation" element={<ProtectedRoute><TechnicianConsolePage /></ProtectedRoute>} />
    <Route path="/app/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
    <Route path="/dashboard" element={<ProtectedRoute><DashboardPage /></ProtectedRoute>} />
    <Route path="/app/onboarding" element={<ProtectedRoute><CmmsConnectPage /></ProtectedRoute>} />
    <Route path="/onboarding" element={<ProtectedRoute><CmmsConnectPage /></ProtectedRoute>} />
    <Route path="/app/voice" element={<ProtectedRoute><VoicePage /></ProtectedRoute>} />
    <Route path="/app/work-orders" element={<ProtectedRoute><WorkOrdersPage /></ProtectedRoute>} />
    <Route path="/work-orders" element={<ProtectedRoute><ProductionWorkOrdersPage /></ProtectedRoute>} />
    <Route path="/work-orders/new" element={<ProtectedRoute><NewWorkOrderPage /></ProtectedRoute>} />
    <Route path="/app/work-orders/:workOrderId" element={<ProtectedRoute><WorkOrderDetailPage /></ProtectedRoute>} />
    <Route path="/work-orders/:workOrderId" element={<ProtectedRoute><ProductionWorkOrderDetailPage /></ProtectedRoute>} />
    <Route path="/app/assets" element={<ProtectedRoute><AssetsPage /></ProtectedRoute>} />
    <Route path="/assets" element={<ProtectedRoute><AssetsPage /></ProtectedRoute>} />
    <Route path="/assets/:assetId" element={<ProtectedRoute><AssetDetailPage /></ProtectedRoute>} />
    <Route path="/app/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
    <Route path="/settings" element={<ProtectedRoute><SettingsPage /></ProtectedRoute>} />
    <Route path="/settings/billing" element={<ProtectedRoute><BillingPage /></ProtectedRoute>} />
    <Route path="*" element={<Navigate to="/" replace />} />
  </Routes>;
}

export default function App() {
  useEffect(() => { document.documentElement.classList.add("dark"); }, []);
  return <ErrorBoundary><AuthProvider><ApplicationRoutes /><Toaster richColors position="top-right" /></AuthProvider></ErrorBoundary>;
}