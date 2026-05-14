import React, { useState } from 'react';
import { Line } from 'react-chartjs-2';
import { AlertTriangle, Droplets, Activity } from 'lucide-react';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend
);

function App() {
  // Mock Data for testing
  const [metrics, setMetrics] = useState({
    rainfall: 95.0,
    upstream: 2.8,
    predictedLevel: 3.59,
    status: 'WARNING: High Flood Risk',
    color: 'text-red-600'
  });

  // Chart Configuration
  const chartData = {
    labels: ['Day 1', 'Day 2', 'Day 3', 'Day 4', 'Day 5'],
    datasets: [
      {
        label: 'Historical Water Level (m)',
        data: [1.3, 2.0, 3.1, 1.1, 4.2],
        borderColor: 'rgb(59, 130, 246)',
        backgroundColor: 'rgba(59, 130, 246, 0.5)',
        tension: 0.3,
      },
    ],
  };

  return (
    <div className="min-h-screen bg-gray-50 p-8 font-sans">
      <div className="max-w-6xl mx-auto">

        {/* Header */}
        <div className="mb-8 border-b pb-4">
          <h1 className="text-3xl font-bold text-gray-800">RIFAR Challenge: Taman Sri Muda</h1>
          <p className="text-gray-500 mt-1">Real-time Flood Monitoring & AI Prediction Dashboard</p>
        </div>

        {/* Top Metric Cards */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">Current Rainfall</p>
              <p className="text-3xl font-bold text-gray-800 mt-1">{metrics.rainfall} mm</p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg text-blue-500">
              <Droplets size={28} />
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">Upstream Level</p>
              <p className="text-3xl font-bold text-gray-800 mt-1">{metrics.upstream} m</p>
            </div>
            <div className="p-3 bg-cyan-50 rounded-lg text-cyan-500">
              <Activity size={28} />
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">AI Predicted Flood Level</p>
              <p className={`text-3xl font-bold mt-1 ${metrics.color}`}>{metrics.predictedLevel} m</p>
              <p className={`text-xs font-bold mt-1 ${metrics.color}`}>{metrics.status}</p>
            </div>
            <div className={`p-3 rounded-lg ${metrics.color === 'text-red-600' ? 'bg-red-50 text-red-500' : 'bg-green-50 text-green-500'}`}>
              <AlertTriangle size={28} />
            </div>
          </div>
        </div>

        {/* Chart Section */}
        <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100">
          <h2 className="text-lg font-bold text-gray-800 mb-4">Water Level Trends</h2>
          <div className="h-[400px]">
            <Line data={chartData} options={{ maintainAspectRatio: false }} />
          </div>
        </div>

      </div>
    </div>
  );
}

export default App;