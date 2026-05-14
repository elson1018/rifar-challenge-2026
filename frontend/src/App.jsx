import React, { useState, useEffect } from 'react';
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

const API = 'http://localhost:8000';

function App() {
  const [rainfall, setRainfall] = useState('80.0');
  const [upstream, setUpstream] = useState('2.5');
  
  const [prediction, setPrediction] = useState({
    predictedLevel: 8.65,
    status: 'DANGER: Severe Flood Risk',
    color: 'text-red-600'
  });

  const [history, setHistory] = useState([1.3, 2.0, 3.1, 1.1, 4.2]);

  useEffect(() => {
    const fetchPrediction = async () => {
      const rainVal = parseFloat(rainfall);
      const upVal = parseFloat(upstream);
      
      if (isNaN(rainVal) || isNaN(upVal)) return;

      try {
        const res = await fetch(`${API}/predict`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            rainfall_mm: rainVal,
            upstream_level_m: upVal
          })
        });
        const data = await res.json();
        
        const level = data.predicted_water_level_m;
        
        let statusText = 'NORMAL: Low Risk';
        let colorText = 'text-green-600';
        
        if (level >= 4.0) {
          statusText = 'DANGER: Severe Flood Risk';
          colorText = 'text-red-600';
        } else if (level >= 3.0) {
          statusText = 'WARNING: High Flood Risk';
          colorText = 'text-yellow-500';
        }

        setPrediction({
          predictedLevel: level.toFixed(2),
          status: statusText,
          color: colorText
        });
        
        setHistory(prev => {
          const newHistory = [...prev, level];
          if (newHistory.length > 10) newHistory.shift();
          return newHistory;
        });

      } catch (error) {
        console.error("Failed to fetch prediction", error);
      }
    };

    const timeoutId = setTimeout(() => {
      fetchPrediction();
    }, 500);

    return () => clearTimeout(timeoutId);
  }, [rainfall, upstream]);

  const chartData = {
    labels: history.map((_, i) => `T-${history.length - 1 - i}`),
    datasets: [
      {
        label: 'Predicted Water Level (m)',
        data: history,
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
              <p className="text-3xl font-bold text-gray-800 mt-1">{rainfall} mm</p>
            </div>
            <div className="p-3 bg-blue-50 rounded-lg text-blue-500">
              <Droplets size={28} />
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">Upstream Level</p>
              <p className="text-3xl font-bold text-gray-800 mt-1">{upstream} m</p>
            </div>
            <div className="p-3 bg-cyan-50 rounded-lg text-cyan-500">
              <Activity size={28} />
            </div>
          </div>

          <div className="bg-white p-6 rounded-xl shadow-sm border border-gray-100 flex items-center justify-between">
            <div>
              <p className="text-sm text-gray-500 font-medium">AI Predicted Flood Level</p>
              <p className={`text-3xl font-bold mt-1 ${prediction.color}`}>{prediction.predictedLevel} m</p>
              <p className={`text-xs font-bold mt-1 ${prediction.color}`}>{prediction.status}</p>
            </div>
            <div className={`p-3 rounded-lg ${prediction.color.includes('red') ? 'bg-red-50 text-red-500' : prediction.color.includes('yellow') ? 'bg-yellow-50 text-yellow-500' : 'bg-green-50 text-green-500'}`}>
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