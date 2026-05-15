import React, { useState, useEffect } from 'react';
import { Line } from 'react-chartjs-2';
import { AlertTriangle, Droplets, Activity, MapPin } from 'lucide-react';
import { MapContainer, TileLayer, Circle, Popup } from 'react-leaflet';
import 'leaflet/dist/leaflet.css';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
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
          if (newHistory.length > 15) newHistory.shift();
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
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.15)',
        tension: 0.4,
        fill: true,
      },
    ],
  };

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900 p-6 lg:p-10 font-sans selection:bg-blue-100">
      <div className="max-w-7xl mx-auto space-y-8">
        
        {/* Header */}
        <header className="flex flex-col md:flex-row md:items-center justify-between gap-4 bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
          <div>
            <h1 className="text-3xl font-extrabold tracking-tight text-slate-900">Taman Sri Muda</h1>
            <p className="text-slate-500 mt-1 font-medium">Real-time Flood Early Warning System</p>
          </div>
        </header>

        <div className="space-y-8">
            
            {/* Metric Cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              {/* Rainfall Card */}
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between transition-all hover:shadow-md">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-blue-50 rounded-xl text-blue-600">
                    <Droplets size={24} strokeWidth={2.5} />
                  </div>
                </div>
                <div>
                  <p className="text-sm text-slate-500 font-semibold mb-1">Current Rainfall</p>
                  <p className="text-4xl font-bold text-slate-900">{parseFloat(rainfall).toFixed(1)} <span className="text-lg text-slate-400 font-medium">mm</span></p>
                </div>
              </div>

              {/* Upstream Card */}
              <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100 flex flex-col justify-between transition-all hover:shadow-md">
                <div className="flex items-center justify-between mb-4">
                  <div className="p-3 bg-cyan-50 rounded-xl text-cyan-600">
                    <Activity size={24} strokeWidth={2.5} />
                  </div>
                </div>
                <div>
                  <p className="text-sm text-slate-500 font-semibold mb-1">Upstream Level</p>
                  <p className="text-4xl font-bold text-slate-900">{parseFloat(upstream).toFixed(2)} <span className="text-lg text-slate-400 font-medium">m</span></p>
                </div>
              </div>

              {/* Prediction Card */}
              <div className={`p-6 rounded-2xl shadow-sm border flex flex-col justify-between transition-all hover:shadow-md ${prediction.color.includes('red') ? 'bg-red-50 border-red-100' : prediction.color.includes('yellow') ? 'bg-yellow-50 border-yellow-100' : 'bg-green-50 border-green-100'}`}>
                <div className="flex items-center justify-between mb-4">
                  <div className={`p-3 rounded-xl ${prediction.color.includes('red') ? 'bg-red-100 text-red-600' : prediction.color.includes('yellow') ? 'bg-yellow-100 text-yellow-600' : 'bg-green-100 text-green-600'}`}>
                    <AlertTriangle size={24} strokeWidth={2.5} />
                  </div>
                </div>
                <div>
                  <p className={`text-sm font-semibold mb-1 ${prediction.color.includes('red') ? 'text-red-700' : prediction.color.includes('yellow') ? 'text-yellow-700' : 'text-green-700'}`}>Predicted Flood Level</p>
                  <p className={`text-4xl font-bold ${prediction.color}`}>{prediction.predictedLevel} <span className="text-lg opacity-70 font-medium">m</span></p>
                  <p className={`text-sm font-bold mt-2 ${prediction.color}`}>{prediction.status}</p>
                </div>
              </div>
            </div>

            {/* Chart Section */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h2 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                <Activity size={20} className="text-blue-500" />
                Predicted Water Level Trend
              </h2>
              <div className="h-[350px] w-full">
                <Line 
                  data={chartData} 
                  options={{ 
                    maintainAspectRatio: false,
                    plugins: {
                      legend: { display: false },
                      tooltip: {
                        backgroundColor: 'rgba(15, 23, 42, 0.9)',
                        padding: 12,
                        titleFont: { size: 14 },
                        bodyFont: { size: 14 },
                        cornerRadius: 8,
                        displayColors: false
                      }
                    },
                    scales: {
                      y: { 
                        beginAtZero: true,
                        grid: { color: '#f1f5f9' },
                        border: { dash: [4, 4] },
                        title: { display: true, text: 'Water Level (m)', color: '#64748b' }
                      },
                      x: {
                        grid: { display: false }
                      }
                    },
                    elements: {
                      line: { borderWidth: 3 },
                      point: { radius: 0, hoverRadius: 6, hitRadius: 10, backgroundColor: '#3b82f6', borderWidth: 2 }
                    }
                  }} 
                />
              </div>
            </div>

            {/* Map Section */}
            <div className="bg-white p-6 rounded-2xl shadow-sm border border-slate-100">
              <h2 className="text-lg font-bold text-slate-800 mb-6 flex items-center gap-2">
                <MapPin size={20} className="text-blue-500" />
                Live Flood Risk Map — Taman Sri Muda
              </h2>
              <div className="h-[400px] w-full rounded-xl overflow-hidden border border-slate-200 z-0">
                <MapContainer center={[3.0296, 101.5288]} zoom={14} scrollWheelZoom={false} className="h-full w-full" style={{ zIndex: 0 }}>
                  <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                  />
                  <Circle 
                    center={[3.0296, 101.5288]} 
                    pathOptions={{ 
                      color: prediction.color.includes('red') ? '#ef4444' : prediction.color.includes('yellow') ? '#eab308' : '#22c55e', 
                      fillColor: prediction.color.includes('red') ? '#ef4444' : prediction.color.includes('yellow') ? '#eab308' : '#22c55e',
                      fillOpacity: 0.4
                    }} 
                    radius={1000} 
                  >
                    <Popup>
                      <div className="text-center font-sans">
                        <strong className="text-slate-800 text-base">Taman Sri Muda</strong><br />
                        <span className="text-sm text-slate-500 mt-1 block">Status: <span className={prediction.color.includes('red') ? 'text-red-600 font-bold' : prediction.color.includes('yellow') ? 'text-yellow-600 font-bold' : 'text-green-600 font-bold'}>{prediction.status}</span></span>
                        <span className="text-sm text-slate-500 block">Predicted Level: <strong>{prediction.predictedLevel}m</strong></span>
                      </div>
                    </Popup>
                  </Circle>
                </MapContainer>
              </div>
            </div>

        </div>
      </div>
    </div>
  );
}

export default App;