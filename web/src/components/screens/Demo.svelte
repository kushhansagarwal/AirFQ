<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import Chart from 'chart.js/auto';
	import { PUBLIC_WS_URL } from '$env/static/public';

  type AirspeedData = {
    airspeed: number;
    timestamp: number;
  };

  let airspeedData: AirspeedData[] = [];
  let websocket: WebSocket;
  let connectionStatus = 'Disconnected';
  let errorMessage = '';
  let chartCanvas: HTMLCanvasElement;
  let chart: Chart;

  // Make x-axis max ticks limit configurable
  export let xAxisMaxTicks: number = 100;

  onMount(() => {
    connectWebSocket();
    initChart();
  });

  onDestroy(() => {
    if (websocket) {
      websocket.close();
    }
    if (chart) {
      chart.destroy();
    }
  });

  function initChart() {
    const ctx = chartCanvas.getContext('2d');
    if (ctx) {
      chart = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: 'Airspeed (m/s)',
            data: [],
            borderColor: 'rgb(75, 192, 192)',
            tension: 0.5, // smoother curve
            fill: false,
            pointRadius: 0, // hide datapoints
            pointHoverRadius: 0 // hide datapoints on hover
          }]
        },
        options: {
          responsive: true,
          animation: {
            duration: 40 // Smooth animation
          },
          scales: {
            x: {
              title: {
                display: true,
                text: 'Time'
              },
              ticks: {
                display: true,
                callback: function() { return ''; }, // show only ticks, no numbers
                autoSkip: true,
                maxTicksLimit: xAxisMaxTicks
              },
              grid: {
                display: true
              }
            },
            y: {
              title: {
                display: true,
                text: 'Airspeed (m/s)'
              },
              min: 0,
              max: 50,
              beginAtZero: true,
              grid: {
                display: true
              }
            }
          },
          plugins: {
            legend: {
              display: true
            }
          }
        }
      });
    }
  }
  function updateChart() {
    if (!chart) return;

    // Use the last 100 data points for better visualization
    const dataToShow = airspeedData.slice(-100);

    // For x axis, just use empty strings for labels to show only ticks
    chart.data.labels = dataToShow.map(() => '');

    chart.data.datasets[0].data = dataToShow.map(d => d.airspeed);
    chart.update();
  }

  function connectWebSocket() {
    try {
      connectionStatus = 'Connecting...';
      websocket = new WebSocket(PUBLIC_WS_URL);
      
      websocket.onopen = () => {
        connectionStatus = 'Connected';
        errorMessage = '';
      };
      
      websocket.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data);
          if (Array.isArray(data)) {
            airspeedData = [...airspeedData, ...data];
            // Sort by timestamp
            airspeedData.sort((a, b) => a.timestamp - b.timestamp);
            updateChart();
          }
        } catch (error) {
          console.error('Error parsing websocket data:', error);
        }
      };
      
      websocket.onerror = (error) => {
        console.error('WebSocket error:', error);
        errorMessage = 'Error connecting to the server';
        connectionStatus = 'Error';
      };
      
      websocket.onclose = () => {
        connectionStatus = 'Disconnected';
      };
    } catch (error) {
      console.error('Error setting up WebSocket:', error);
      errorMessage = 'Failed to set up WebSocket connection';
      connectionStatus = 'Error';
    }
  }

  function clearData() {
    airspeedData = [];
    if (chart) {
      chart.data.labels = [];
      chart.data.datasets[0].data = [];
      chart.update();
    }
  }
</script>

<div class="flex flex-col gap-6">
  <h1 class="text-4xl font-bold">Airspeed Data Demo</h1>
  
  <div class="flex items-center gap-4">
    <div class="badge {connectionStatus === 'Connected' ? 'badge-success' : connectionStatus === 'Connecting...' ? 'badge-warning' : 'badge-error'}">
      {connectionStatus}
    </div>
    {#if errorMessage}
      <div class="text-error">{errorMessage}</div>
    {/if}
    <button class="btn btn-sm btn-primary" on:click={connectWebSocket} disabled={connectionStatus === 'Connected' || connectionStatus === 'Connecting...'}>
      Reconnect
    </button>
    <button class="btn btn-sm btn-secondary" on:click={clearData}>
      Clear Data
    </button>
  </div>

  <div class="card bg-base-100 p-4">
    <div class="w-full">
      <canvas bind:this={chartCanvas}></canvas>
    </div>
  </div>
</div>