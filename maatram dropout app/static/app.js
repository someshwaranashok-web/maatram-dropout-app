async function fetchStudents() {
  const res = await fetch('/api/students');
  const data = await res.json();
  return data;
}

function populateTable(students) {
  const tbody = document.querySelector('#studentsTable tbody');
  tbody.innerHTML = '';
  students.forEach(s => {
    const tr = document.createElement('tr');
    tr.innerHTML = `
      <td>${s.name}</td>
      <td>${(s.score || 0).toFixed(2)}</td>
      <td>${s.risk}</td>
      <td>${s.reason}</td>
      <td>${s.created_at ? new Date(s.created_at).toLocaleString() : ''}</td>
    `;
    tbody.appendChild(tr);
  });
}

function drawChart(students) {
  // Count risk categories and average scores
  const counts = { 'Low Risk': 0, 'Medium Risk': 0, 'High Risk': 0 };
  students.forEach(s => {
    counts[s.risk] = (counts[s.risk] || 0) + 1;
  });

  const ctx = document.getElementById('riskChart').getContext('2d');
  if (window.riskChart) {
    window.riskChart.destroy();
  }
  window.riskChart = new Chart(ctx, {
    type: 'bar',
    data: {
      labels: ['Low Risk','Medium Risk','High Risk'],
      datasets: [{
        label: 'Number of students',
        data: [counts['Low Risk'], counts['Medium Risk'], counts['High Risk']]
      }]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false
    }
  });
}

(async function init() {
  const students = await fetchStudents();
  populateTable(students);
  drawChart(students);
})();

