function parseUtcTimestamp(ts) {
  var normalized = ts.trim().replace(' ', 'T');
  var parsed = new Date(normalized + 'Z');
  if (!isNaN(parsed)) {
    return parsed;
  }
  var match = ts.match(/^\s*(\d{4})-(\d{2})-(\d{2})[ T](\d{2}):(\d{2}):(\d{2})\s*$/);
  if (!match) {
    return new Date(ts);
  }
  var year = parseInt(match[1], 10);
  var month = parseInt(match[2], 10) - 1;
  var day = parseInt(match[3], 10);
  var hour = parseInt(match[4], 10);
  var minute = parseInt(match[5], 10);
  var second = parseInt(match[6], 10);
  return new Date(Date.UTC(year, month, day, hour, minute, second));
}

document.addEventListener('DOMContentLoaded', function(){
  document.querySelectorAll('.tx-ts').forEach(function(el){
    var ts = el.getAttribute('data-ts');
    if (!ts) return;
    var d = parseUtcTimestamp(ts);
    if (!isNaN(d)) {
      el.textContent = d.toLocaleString();
    }
  });

  const flashes = document.querySelectorAll('.flash');
  if (flashes.length) {
    setTimeout(function () {
      flashes.forEach(function (f) { f.classList.add('hide'); });
    }, 4000);
    flashes.forEach(function (f) {
      f.addEventListener('transitionend', function () {
        if (f.classList.contains('hide') && f.parentNode) f.parentNode.removeChild(f);
      });
    });
  }

  document.querySelectorAll('.remove-child-form').forEach(function (form) {
    form.addEventListener('submit', function (event) {
      if (!confirm('Are you sure you want to remove this child? This action cannot be undone.')) {
        event.preventDefault();
      }
    });
  });
});

// Dark Mode Toggle
document.addEventListener('DOMContentLoaded', function() {
  const htmlTheme = document.documentElement.getAttribute('data-theme');
  const bodyTheme = document.body.getAttribute('data-theme');
  const themeAttr = htmlTheme || bodyTheme;
  const stored = localStorage.getItem('darkMode');
  let isDarkMode;

  if (themeAttr === 'light') {
    isDarkMode = false;
  } else if (themeAttr === 'dark') {
    isDarkMode = true;
  } else if (stored !== null) {
    isDarkMode = stored === 'true';
  } else {
    isDarkMode = true;
  }

  function applyTheme(darkMode) {
    const theme = darkMode ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', theme);
    document.body.setAttribute('data-theme', theme);
  }

  applyTheme(isDarkMode);

  const darkModeToggle = document.getElementById('dark-mode-toggle');
  if (darkModeToggle) {
    darkModeToggle.checked = isDarkMode;

    darkModeToggle.addEventListener('change', function() {
      const enabled = this.checked;
      applyTheme(enabled);
      localStorage.setItem('darkMode', String(enabled));

      // Try to persist preference server-side for logged-in users
      fetch('/set_dark_mode', {
        method: 'POST',
        credentials: 'same-origin',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({ dark: enabled })
      }).catch(function(err) {
        console.debug('Failed to update server dark mode:', err);
      });
    });
  }
});
