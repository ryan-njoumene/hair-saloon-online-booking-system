function showSection(section) {
  const sections = ['users', 'appointments', 'reports', 'secret'];
  sections.forEach(id => {
    document.getElementById('section-' + id).style.display = (id === section) ? 'block' : 'none';
  });

  const navLinks = document.querySelectorAll('#api-nav a');
  navLinks.forEach(link => {
    link.classList.remove('active-link');
    if (link.textContent.toLowerCase() === section) {
      link.classList.add('active-link');
    }
  });

  const baseUrl = window.location.origin;
  document.querySelectorAll('.endpoint-url').forEach(el => {
    const path = el.dataset.url;
    el.textContent = `curl ${baseUrl}${path}`;
  });
}

async function fetchApi(endpoint) {
  const fullUrl = window.location.origin + endpoint;
  const resultBox = document.getElementById('api-result');
  resultBox.textContent = "⏳ Fetching from " + fullUrl + " ...";

  try {
    const res = await fetch(fullUrl, {
      headers: { 'Content-Type': 'application/json' }
    });

    const isJson = res.headers.get('Content-Type')?.includes('application/json');
    const data = isJson ? await res.json() : await res.text();
    resultBox.textContent = isJson ? JSON.stringify(data, null, 2) : data;
  } catch (err) {
    resultBox.textContent = "❌ Error: " + err.message;
  }
}

function fetchById(basePath, inputId) {
  const id = document.getElementById(inputId).value.trim();
  const resultBox = document.getElementById('api-result');

  if (!id) {
    resultBox.textContent = "⚠️ Please enter a valid ID.";
    return;
  }

  const fullPath = basePath + id;
  const fullUrl = window.location.origin + fullPath;

  const previewCode = document.getElementById(inputId.replace('-input', '-url-preview'));
  if (previewCode) previewCode.textContent = `curl ${fullUrl}`;

  resultBox.textContent = "⏳ Fetching " + fullUrl + " ...";

  fetch(fullUrl, { headers: { 'Content-Type': 'application/json' } })
    .then(res => res.headers.get("Content-Type")?.includes("json") ? res.json() : res.text())
    .then(data => {
      resultBox.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
    })
    .catch(err => {
      resultBox.textContent = "❌ Error: " + err.message;
    });
}
