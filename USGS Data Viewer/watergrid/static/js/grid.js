document.addEventListener('DOMContentLoaded', () => {
  console.log('Fetching /data');
  fetch('/data')
    .then(res => res.json())
    .then(data => {
      console.log('Raw data:', data);
      
      // Handle error responses from server
      if (data.error) {
        throw new Error(data.message || 'Server error');
      }
      
      // Handle USGS water services JSON structure
      let rows;
      if (Array.isArray(data)) {
        rows = data;
      } else if (data && Array.isArray(data.value)) {
        rows = data.value;
      } else if (data && data.value && Array.isArray(data.value.timeSeries)) {
        // Handle USGS timeSeriesResponseType structure
        // Group by site to avoid duplicate site names
        const siteMap = new Map();
        
        data.value.timeSeries.forEach(series => {
          const site = series.sourceInfo;
          const variable = series.variable;
          const latestValue = series.values && series.values[0] && series.values[0].value && series.values[0].value[0];
          
          const siteCode = site.siteCode[0].value;
          const variableInfo = {
            name: variable.variableName.replace(/<\/?[^>]+(>|$)/g, ""), // Strip HTML tags
            value: latestValue ? latestValue.value : 'No data',
            unit: variable.unit.unitCode,
            dateTime: latestValue ? latestValue.dateTime : 'No data',
            qualifiers: latestValue && latestValue.qualifiers ? latestValue.qualifiers.join(', ') : ''
          };
          
          if (siteMap.has(siteCode)) {
            // Add variable to existing site
            siteMap.get(siteCode).variables.push(variableInfo);
          } else {
            // Create new site entry
            siteMap.set(siteCode, {
              siteName: site.siteName,
              siteCode: siteCode,
              latitude: site.geoLocation.geogLocation.latitude,
              longitude: site.geoLocation.geogLocation.longitude,
              variables: [variableInfo]
            });
          }
        });
        
        // Convert to rows with one row per site, showing key measurements
        rows = Array.from(siteMap.values()).map(site => {
          // Find common measurements
          const temp = site.variables.find(v => v.name.toLowerCase().includes('temperature'));
          const ph = site.variables.find(v => v.name.toLowerCase().includes('ph'));
          const oxygen = site.variables.find(v => v.name.toLowerCase().includes('oxygen'));
          const salinity = site.variables.find(v => v.name.toLowerCase().includes('salinity'));
          const elevation = site.variables.find(v => v.name.toLowerCase().includes('elevation'));
          
          return {
            siteName: site.siteName,
            siteCode: site.siteCode,
            latitude: Number.isFinite(site.latitude) ? site.latitude.toFixed(4) : 'N/A',
            longitude: Number.isFinite(site.longitude) ? site.longitude.toFixed(4) : 'N/A',
            variableCount: site.variables.length,
            temperature: temp ? `${temp.value} ${temp.unit}` : 'N/A',
            pH: ph ? ph.value : 'N/A',
            dissolvedOxygen: oxygen ? `${oxygen.value} ${oxygen.unit}` : 'N/A',
            salinity: salinity ? `${salinity.value} ${salinity.unit}` : 'N/A',
            waterElevation: elevation ? `${elevation.value} ${elevation.unit}` : 'N/A',
            lastUpdate: temp ? temp.dateTime.split('T')[0] : 'N/A' // Just the date part
          };
        });
      } else if (data && Array.isArray(data.features)) {
        // Support GeoJSON FeatureCollection from USGS
        rows = data.features.map(item => item.properties || {});
      } else {
        console.error('Expected array, object with .value, USGS timeSeries, or GeoJSON .features');
        console.error('Received:', data);
        return;
      }

      console.log('Processed rows:', rows);

      const table = document.querySelector('table');
      const theadRow = table.querySelector('thead tr');
      const tbody = table.querySelector('tbody');

      // Clear loading row
      tbody.innerHTML = '';

      if (rows.length === 0) {
        const tr = document.createElement('tr');
        const td = document.createElement('td');
        td.textContent = 'No data available';
        td.colSpan = 10;
        tr.appendChild(td);
        tbody.appendChild(tr);
        return;
      }

      // Determine columns from keys of first object
      const cols = Object.keys(rows[0] || {});
      
      // Create more readable column headers
      const columnLabels = {
        siteName: 'Site Name',
        siteCode: 'Site Code',
        latitude: 'Latitude',
        longitude: 'Longitude',
        variableCount: '# Variables',
        temperature: 'Temperature',
        pH: 'pH',
        dissolvedOxygen: 'Dissolved O₂',
        salinity: 'Salinity',
        waterElevation: 'Water Level',
        lastUpdate: 'Last Update'
      };
      
      cols.forEach(col => {
        const th = document.createElement('th');
        th.setAttribute('role', 'columnheader');
        th.textContent = columnLabels[col] || col.charAt(0).toUpperCase() + col.slice(1);
        theadRow.appendChild(th);
      });

      rows.forEach((row, rowIndex) => {
        const tr = document.createElement('tr');
        tr.setAttribute('role', 'row');
        tr.tabIndex = 0;
        cols.forEach(col => {
          const td = document.createElement('td');
          td.setAttribute('role', 'gridcell');
          td.textContent = row[col] || '';
          tr.appendChild(td);
        });
        tbody.appendChild(tr);
      });
    })
    .catch(err => {
      console.error('Error fetching data:', err);
      const tbody = document.querySelector('tbody');
      tbody.innerHTML = `
        <tr>
          <td colspan="10" class="error">
            <strong>Error loading data:</strong><br>
            ${err.message}<br><br>
            <small>Please ensure 'waterservices.usgs.gov.json' is placed in the application directory, data folder, Downloads, or Desktop.</small>
          </td>
        </tr>
      `;
    });
});