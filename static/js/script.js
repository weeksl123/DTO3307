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
  if (!flashes.length) return;
  setTimeout(function () {
    flashes.forEach(function (f) { f.classList.add('hide'); });
  }, 4000);
  flashes.forEach(function (f) {
    f.addEventListener('transitionend', function () {
      if (f.classList.contains('hide') && f.parentNode) f.parentNode.removeChild(f);
    });
  });
});

// Dark Mode Toggle
document.addEventListener('DOMContentLoaded', function() {
  const darkModeToggle = document.getElementById('dark-mode-toggle');
  
  if (darkModeToggle) {
    // Check if dark mode was previously set
    const isDarkMode = localStorage.getItem('darkMode') === 'true';
    darkModeToggle.checked = isDarkMode;
    
    if (isDarkMode) {
      document.documentElement.setAttribute('data-theme', 'dark');
    }
    
    // Toggle dark mode
    darkModeToggle.addEventListener('change', function() {
      if (this.checked) {
        document.documentElement.setAttribute('data-theme', 'dark');
        localStorage.setItem('darkMode', 'true');
      } else {
        document.documentElement.removeAttribute('data-theme');
        localStorage.setItem('darkMode', 'false');
      }
    });
  }
});
