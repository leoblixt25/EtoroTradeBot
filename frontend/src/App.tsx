import { Routes, Route } from 'react-router-dom';
import { ThemeProvider } from './context/ThemeContext';
import Layout from './components/Layout';
import Dashboard from './pages/Dashboard';
import Portfolio from './pages/Portfolio';
import Traders from './pages/Traders';
import Analytics from './pages/Analytics';
import AIRecommendations from './pages/AIRecommendations';
import Settings from './pages/Settings';

export default function App() {
  return (
    <ThemeProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Dashboard />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/traders" element={<Traders />} />
          <Route path="/analytics" element={<Analytics />} />
          <Route path="/recommendations" element={<AIRecommendations />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
      </Routes>
    </ThemeProvider>
  );
}
