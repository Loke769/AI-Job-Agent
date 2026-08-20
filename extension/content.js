// Tsenta-style toolbar: detects ATS form, shows "Auto-fill ready"
(function(){
  const fields = document.querySelectorAll('input, textarea, select');
  if(fields.length>0){
    const bar = document.createElement('div');
    bar.style.cssText='position:fixed;top:10px;right:10px;background:#1a1d23;color:#e5e7eb;padding:10px 14px;border-radius:10px;z-index:99999;border:1px solid #2a2e36;font-family:system-ui;font-size:13px;';
    bar.innerHTML = `AI Job Agent • ${fields.length} fields detected <button id="tsenta-apply" style="margin-left:8px;background:#6ee7b7;border:0;padding:6px 10px;border-radius:8px;cursor:pointer;font-weight:600">Apply</button>`;
    document.body.appendChild(bar);
    document.getElementById('tsenta-apply').onclick = ()=> alert('AI Job Agent would now tailor & fill this ATS form. Run python -m src.pipeline --apply for demo.');
  }
})();
