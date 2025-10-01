// USGS Water Data Explorer
const app = {
  data: [],
  allData: [],
  currentIndex: 0,
  charts: {},
  isPlaying: false,
  playInterval: null,
  currentSite: 'all',
  sites: [],
  siteInfo: {},
  
  init() {
    this.fetchSiteInfo();
    this.fetchData();
  },
  
  async fetchSiteInfo() {
    try {
      const response = await fetch('/site-info');
      const data = await response.json();
      const sites = data.sites || [];
      
      // Store site info as lookup
      this.siteInfo = {};
      sites.forEach(site => {
        this.siteInfo[site.site_no] = site;
        this.sites.push(site.site_no);
      });
      
      // Populate site selector with location details
      const selector = document.getElementById('site-selector');
      sites.forEach(site => {
        const option = document.createElement('option');
        option.value = site.site_no;
        option.textContent = `${site.station_nm} (${site.latitude.toFixed(3)}°N, ${Math.abs(site.longitude).toFixed(3)}°W)`;
        selector.appendChild(option);
      });
      
      selector.addEventListener('change', (e) => {
        this.currentSite = e.target.value;
        this.filterDataBySite();
      });
      
    } catch (error) {
      console.error('Failed to load site information:', error);
    }
  },
  
  async fetchData() {
    try {
      const response = await fetch('/data');
      const data = await response.json();
      
      if (data.error) {
        this.showError(data.message);
        return;
      }
      
      this.allData = data;
      this.filterDataBySite();
      
    } catch (error) {
      this.showError(`Failed to load data: ${error.message}`);
    }
  },
  
  filterDataBySite() {
    if (this.currentSite === 'all') {
      this.data = this.allData;
    } else {
      this.data = this.allData.filter(d => d.Site === this.currentSite);
    }
    
    this.currentIndex = this.data.length - 1; // Start at latest
    
    document.getElementById('record-count').textContent = this.data.length;
    document.getElementById('time-slider').max = Math.max(0, this.data.length - 1);
    document.getElementById('time-slider').value = this.currentIndex;
    
    this.updateDisplay();
    
    // Create charts if they don't exist, otherwise just update
    if (Object.keys(this.charts).length === 0) {
      this.createCharts();
    } else {
      this.updateCharts();
    }
    
    this.setupEventListeners();
  },
  
  setupEventListeners() {
    const slider = document.getElementById('time-slider');
    slider.addEventListener('input', (e) => {
      this.currentIndex = parseInt(e.target.value);
      this.updateDisplay();
    });
  },
  
  updateDisplay() {
    if (!this.data || this.data.length === 0) {
      document.getElementById('current-time').textContent = 'No data';
      return;
    }
    
    const currentData = this.data[this.currentIndex];
    
    // Update time display
    const timeDisplay = document.getElementById('current-time');
    const siteInfo = currentData.Site ? ` (Site: ${currentData.Site})` : '';
    timeDisplay.textContent = new Date(currentData.Datetime).toLocaleString() + siteInfo;
    
    // Update last update info
    const lastUpdate = document.getElementById('last-update');
    lastUpdate.textContent = new Date(this.data[this.data.length - 1].Datetime).toLocaleString();
    
    // Update value cards
    this.updateValueCards(currentData);
    
    // Update charts
    this.updateCharts();
  },
  
  updateValueCards(data) {
    const measurements = [
      { key: 'Water Temperature (°C)', label: 'Water Temp', unit: '°C', color: '#ff5722' },
      { key: 'Dissolved Oxygen (mg/L)', label: 'Dissolved O₂', unit: 'mg/L', color: '#4caf50' },
      { key: 'Dissolved Oxygen Saturation (%)', label: 'DO Saturation', unit: '%', color: '#8bc34a' },
      { key: 'Gage Height (ft)', label: 'Water Level', unit: 'ft', color: '#2196f3' },
      { key: 'Turbidity (NTU)', label: 'Turbidity', unit: 'NTU', color: '#795548' }
    ];
    
    const container = document.getElementById('latest-values');
    container.innerHTML = measurements.map(m => {
      const value = data[m.key];
      const displayValue = value !== null && value !== undefined ? value.toFixed(2) : 'N/A';
      return `
        <div class="value-card" style="border-left-color: ${m.color}">
          <h3>${m.label}</h3>
          <p class="value" style="color: ${m.color}">
            ${displayValue}
            <span class="unit">${value !== null && value !== undefined ? m.unit : ''}</span>
          </p>
        </div>
      `;
    }).join('');
  },
  
  createCharts() {
    const chartsConfig = [
      {
        id: 'temp-chart',
        title: 'Water Temperature',
        dataKey: 'Water Temperature (°C)',
        unit: '°C',
        color: 'rgb(255, 87, 34)',
        bgColor: 'rgba(255, 87, 34, 0.1)'
      },
      {
        id: 'do-chart',
        title: 'Dissolved Oxygen',
        dataKey: 'Dissolved Oxygen (mg/L)',
        unit: 'mg/L',
        color: 'rgb(76, 175, 80)',
        bgColor: 'rgba(76, 175, 80, 0.1)'
      },
      {
        id: 'level-chart',
        title: 'Water Level',
        dataKey: 'Gage Height (ft)',
        unit: 'ft',
        color: 'rgb(33, 150, 243)',
        bgColor: 'rgba(33, 150, 243, 0.1)'
      },
      {
        id: 'turbidity-chart',
        title: 'Turbidity',
        dataKey: 'Turbidity (NTU)',
        unit: 'NTU',
        color: 'rgb(121, 85, 72)',
        bgColor: 'rgba(121, 85, 72, 0.1)'
      }
    ];
    
    const chartsGrid = document.getElementById('charts-grid');
    chartsGrid.innerHTML = chartsConfig.map(config => `
      <div class="chart-container">
        <h3>${config.title}</h3>
        <div class="chart-wrapper">
          <canvas id="${config.id}"></canvas>
        </div>
      </div>
    `).join('');
    
    chartsConfig.forEach(config => {
      const ctx = document.getElementById(config.id).getContext('2d');
      this.charts[config.id] = new Chart(ctx, {
        type: 'line',
        data: {
          labels: [],
          datasets: [{
            label: `${config.title} (${config.unit})`,
            data: [],
            borderColor: config.color,
            backgroundColor: config.bgColor,
            borderWidth: 3,
            tension: 0.4,
            fill: true,
            pointRadius: 2,
            pointHoverRadius: 8,
            pointBackgroundColor: config.color,
            pointBorderColor: '#fff',
            pointBorderWidth: 2
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: { display: false },
            tooltip: {
              mode: 'index',
              intersect: false
            }
          },
          scales: {
            x: {
              display: true,
              ticks: {
                maxTicksLimit: 10,
                maxRotation: 45,
                minRotation: 45
              }
            },
            y: {
              display: true,
              beginAtZero: false
            }
          },
          interaction: {
            mode: 'nearest',
            axis: 'x',
            intersect: false
          }
        }
      });
      
      config.chart = this.charts[config.id];
      config.fullData = this.data;
    });
    
    this.updateCharts();
  },
  
  updateCharts() {
    // Get window of data around current index (e.g., 100 points)
    const windowSize = 200;
    const startIdx = Math.max(0, this.currentIndex - windowSize);
    const endIdx = Math.min(this.data.length, this.currentIndex + 1);
    const windowData = this.data.slice(startIdx, endIdx);
    
    Object.keys(this.charts).forEach(chartId => {
      const chart = this.charts[chartId];
      const config = this.getChartConfig(chartId);
      
      const labels = windowData.map(d => {
        const date = new Date(d.Datetime);
        return date.toLocaleTimeString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' });
      });
      
      const values = windowData.map(d => d[config.dataKey]);
      
      chart.data.labels = labels;
      chart.data.datasets[0].data = values;
      chart.update('none'); // Update without animation for smooth scrubbing
    });
  },
  
  getChartConfig(chartId) {
    const configs = {
      'temp-chart': { dataKey: 'Water Temperature (°C)' },
      'do-chart': { dataKey: 'Dissolved Oxygen (mg/L)' },
      'level-chart': { dataKey: 'Gage Height (ft)' },
      'turbidity-chart': { dataKey: 'Turbidity (NTU)' }
    };
    return configs[chartId];
  },
  
  showLatest() {
    this.currentIndex = this.data.length - 1;
    document.getElementById('time-slider').value = this.currentIndex;
    this.updateDisplay();
  },
  
  stepBack() {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      document.getElementById('time-slider').value = this.currentIndex;
      this.updateDisplay();
    }
  },
  
  stepForward() {
    if (this.currentIndex < this.data.length - 1) {
      this.currentIndex++;
      document.getElementById('time-slider').value = this.currentIndex;
      this.updateDisplay();
    }
  },
  
  playTimeline() {
    const playBtn = document.getElementById('play-btn');
    
    if (this.isPlaying) {
      // Stop playing
      this.isPlaying = false;
      clearInterval(this.playInterval);
      playBtn.textContent = '▶ Play';
      playBtn.classList.remove('secondary');
    } else {
      // Start playing
      this.isPlaying = true;
      playBtn.textContent = '⏸ Pause';
      playBtn.classList.add('secondary');
      
      this.playInterval = setInterval(() => {
        if (this.currentIndex >= this.data.length - 1) {
          // Loop back to start
          this.currentIndex = 0;
        } else {
          this.currentIndex++;
        }
        document.getElementById('time-slider').value = this.currentIndex;
        this.updateDisplay();
      }, 100); // Update every 100ms for smooth animation
    }
  },
  
  showError(message) {
    const container = document.getElementById('latest-values');
    container.innerHTML = `<div class="error"><strong>Error:</strong> ${message}</div>`;
  }
};

// Initialize when DOM is ready
if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => app.init());
} else {
  app.init();
}
