from __future__ import annotations
import json
import time
from fastapi import FastAPI, Request, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from ..config import resolve_path, get_settings, ensure_dirs
from ..resume_parser import load_profile
from ..apply.tracker import load_applications, get_stats
import yaml

app = FastAPI(title="AI Job Agent")

app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

# ===== Production UI — inspired by screenshot, original code =====
DASH_HTML = r"""
<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>AI Job Agent — Dashboard</title>
<script src="https://cdn.tailwindcss.com"></script>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400&display=swap" rel="stylesheet">
<style>
*{font-family:Inter,system-ui,sans-serif}
.scrollbar-hide::-webkit-scrollbar{display:none}
.scrollbar-hide{-ms-overflow-style:none;scrollbar-width:none}
.match-ring{position:relative;width:44px;height:44px;border-radius:999px;display:grid;place-items:center;font-size:11px;font-weight:700}
.match-ring::before{content:"";position:absolute;inset:0;border-radius:999px;background:conic-gradient(#0f172a calc(var(--p)*1%), #e5e7eb 0); -webkit-mask: radial-gradient(circle, transparent 16px, black 17px); mask: radial-gradient(circle, transparent 16px, black 17px);}
</style>
</head>
<body class="bg-[#F8F7F3] text-slate-900">
<div class="flex min-h-screen">
  <!-- Left sidebar — chat assistant -->
  <aside class="hidden lg:flex w-[300px] shrink-0 flex-col border-r border-stone-200 bg-white">
    <div class="h-[56px] flex items-center justify-between px-4 border-b border-stone-100">
      <div class="flex items-center gap-2">
        <span class="text-sm font-semibold">New chat</span>
        <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12h14"/></svg>
      </div>
      <button class="h-7 w-7 grid place-items-center rounded-full hover:bg-stone-100">✕</button>
    </div>
    <div class="flex-1 overflow-auto p-4">
      <div class="text-center py-6">
        <div class="text-[17px] font-semibold">How can I help?</div>
        <p class="mt-2 text-[12.5px] leading-5 text-stone-500 px-2">Ask me anything about your job search: tune your feed, apply to matches, track your applications, or learn how the agent works. Every change is previewed, approved by you, and undoable.</p>
      </div>
      <div class="mt-4 space-y-2.5">
        <button onclick="fillChat('Why are my recommendations...')" class="w-full flex items-center gap-3 px-3 py-3 rounded-2xl border border-stone-200 bg-white hover:bg-stone-50 text-left text-[13px] font-medium">
          <span class="h-8 w-8 rounded-full bg-emerald-900 text-white grid place-items-center">≡</span> Why are my recommendatio...
        </button>
        <button onclick="triggerApplyTop()" class="w-full flex items-center gap-3 px-3 py-3 rounded-2xl border border-stone-200 bg-white hover:bg-stone-50 text-left text-[13px] font-medium">
          <span class="h-8 w-8 rounded-full bg-emerald-900 text-white grid place-items-center">⚡</span> Apply to my top matches
        </button>
        <button onclick="switchTab('tracker')" class="w-full flex items-center gap-3 px-3 py-3 rounded-2xl border border-stone-200 bg-white hover:bg-stone-50 text-left text-[13px] font-medium">
          <span class="h-8 w-8 rounded-full bg-[#C7B7A6] text-white grid place-items-center">▭</span> Where are my applications?
        </button>
      </div>
    </div>
    <div class="p-3 border-t border-stone-100">
      <div class="rounded-2xl border border-stone-200 bg-white p-2 flex items-center gap-2">
        <input id="chatInput" placeholder="Ask about your feed, applications, or anything..." class="flex-1 px-3 py-2 text-[13px] placeholder:text-stone-400 focus:outline-none">
        <button onclick="sendChat()" class="h-8 w-8 rounded-full bg-stone-900 text-white grid place-items-center">↑</button>
      </div>
    </div>
  </aside>

  <!-- Main -->
  <div class="flex-1 min-w-0 flex flex-col">
    <!-- Top nav -->
    <header class="h-[56px] sticky top-0 z-20 bg-[#F8F7F3]/90 backdrop-blur border-b border-stone-200 flex items-center justify-between px-4 gap-4">
      <nav class="flex items-center gap-1 overflow-auto scrollbar-hide">
        <a onclick="switchTab('dashboard');return false" href="#dashboard" class="nav-link px-3.5 py-2 rounded-full bg-white border border-stone-200 text-sm font-semibold shadow-sm">Dashboard</a>
        <a onclick="switchTab('browse');return false" href="#browse" class="nav-link px-3 py-1.5 text-sm text-stone-600 hover:text-stone-900">Browse jobs</a>
        <a onclick="switchTab('auto');return false" href="#auto" class="nav-link px-3 py-1.5 text-sm text-stone-600 hover:text-stone-900">Auto Apply</a>
        <a onclick="switchTab('tracker');return false" href="#tracker" class="nav-link px-3 py-1.5 text-sm text-stone-600 hover:text-stone-900">Tracker</a>
        <a onclick="switchTab('network');return false" href="#network" class="nav-link px-3 py-1.5 text-sm text-stone-600 hover:text-stone-900 hidden sm:inline">Networking</a>
        <a onclick="switchTab('profile');return false" href="#profile" class="nav-link px-3 py-1.5 text-sm text-stone-600 hover:text-stone-900">Profile</a>
        <a onclick="switchTab('research');return false" href="#research" class="nav-link px-3 py-1.5 text-sm text-stone-600 hover:text-stone-900 hidden md:inline">Research</a>
      </nav>
      <div class="flex items-center gap-2 shrink-0">
        <a onclick="switchTab('profile');return false" href="#profile" class="text-sm text-stone-600 hover:text-stone-900">Settings</a>
        <span class="hidden sm:inline-flex items-center gap-1.5 px-3 py-1.5 rounded-full bg-[#0F2A1A] text-amber-300 text-xs font-semibold"><span class="h-2 w-2 rounded-full bg-amber-400"></span><span id="leftCount">0</span> left</span>
        <button class="h-8 w-8 rounded-full bg-stone-900 text-white grid place-items-center sm:hidden" onclick="document.querySelector('aside').classList.toggle('hidden')">☰</button>
      </div>
    </header>

    <div class="flex-1 overflow-auto">
      <div class="max-w-[1220px] mx-auto px-4 py-4">

        <!-- Search + filters -->
        <div class="rounded-2xl border border-stone-200 bg-white p-3 shadow-sm">
          <div class="flex items-center gap-3">
            <div class="hidden sm:flex items-center gap-1.5 px-3 py-2 rounded-full bg-stone-50 border border-stone-200 text-xs font-medium">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8"><path d="M4 6h16M4 12h16M4 18h16"/></svg>
              Title + description
              <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>
            </div>
            <div class="flex-1 flex items-center gap-2 px-3 py-2 rounded-full bg-stone-50 border border-stone-200">
              <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#9ca3af" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3-3"/></svg>
              <input id="search" placeholder="Search by title or keyword..." class="flex-1 bg-transparent text-sm placeholder:text-stone-400 focus:outline-none">
            </div>
          </div>
          <div class="mt-3 rounded-xl bg-stone-50 border border-stone-100 px-3 py-2 flex items-center gap-2">
            <span class="text-xs font-semibold text-stone-500">Exclude</span>
            <input id="exclude" placeholder="Hide jobs mentioning..." class="flex-1 bg-transparent text-sm placeholder:text-stone-400 focus:outline-none">
          </div>
          <div class="mt-3 flex flex-wrap items-center gap-2 text-xs">
            <button class="filter-pill px-3 py-1.5 rounded-full border border-stone-200 bg-white flex items-center gap-1">Date <span class="text-stone-400">▾</span></button>
            <button class="filter-pill px-3 py-1.5 rounded-full border border-stone-200 bg-white flex items-center gap-1">📍 Location <span class="text-stone-400">▾</span></button>
            <button class="filter-pill px-3 py-1.5 rounded-full border border-stone-200 bg-white">Workplace <span class="text-stone-400">▾</span></button>
            <button class="filter-pill px-3 py-1.5 rounded-full border border-stone-200 bg-white">🏢 Companies <span class="text-stone-400">▾</span></button>
            <span class="h-5 w-px bg-stone-200"></span>
            <button class="filter-pill px-3 py-1.5 rounded-full border border-stone-200 bg-white">Degree Level <span class="text-stone-400">▾</span></button>
            <button class="filter-pill px-3 py-1.5 rounded-full border border-stone-200 bg-white">Max Experience <span class="text-stone-400">▾</span></button>
            <button class="filter-pill px-3 py-1.5 rounded-full border border-stone-200 bg-white">Sponsors Visa <span class="text-stone-400">▾</span></button>
            <button class="filter-pill px-3 py-1.5 rounded-full border border-stone-200 bg-white">Role <span class="text-stone-400">▾</span></button>
            <button onclick="runPipeline()" class="ml-auto px-3 py-1.5 rounded-full bg-white border border-stone-200 flex items-center gap-1.5 font-medium">⚙️ Apply <span class="text-stone-400">▾</span></button>
          </div>
          <div class="mt-2 flex flex-wrap gap-2 text-xs">
            <button class="px-3 py-1.5 rounded-full border border-stone-200 bg-white">Job Type <span class="text-stone-400">▾</span></button>
            <button class="px-3 py-1.5 rounded-full border border-stone-200 bg-white">Employment Type <span class="text-stone-400">▾</span></button>
          </div>
        </div>

        <!-- Out of free banner -->
        <div id="freeBanner" class="mt-4 rounded-2xl border border-stone-200 bg-white p-4 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <div class="flex items-center gap-3">
            <div class="h-9 w-9 rounded-xl bg-stone-100 grid place-items-center">✦</div>
            <div>
              <div class="text-sm font-semibold">You're out of free applications</div>
              <div class="text-xs text-stone-500">Unlock more applications with a plan. Dry-run is always free.</div>
            </div>
          </div>
          <button onclick="switchTab('profile')" class="px-4 py-2 rounded-full bg-[#0F2A1A] text-white text-sm font-medium">See plans →</button>
        </div>

        <!-- Dashboard pane -->
        <section id="pane-dashboard" class="">
          <div class="mt-6 flex items-center justify-between">
            <h2 class="text-[15px] font-semibold">Top job matches</h2>
            <div class="flex items-center gap-2">
              <button class="hidden sm:inline-flex px-3 py-1.5 rounded-full border border-stone-200 bg-white text-xs font-medium">+ Add your own</button>
              <button onclick="switchTab('browse')" class="px-3 py-1.5 rounded-full border border-stone-200 bg-white text-xs font-medium">☰ Browse jobs</button>
              <button onclick="approveAll()" class="px-4 py-2 rounded-full bg-[#0F2A1A] text-white text-xs font-semibold flex items-center gap-1">✦ Apply to all <span id="applyAllCount">5</span> →</button>
            </div>
          </div>

          <div id="jobCards" class="mt-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-3"></div>
          <div id="emptyCards" class="hidden mt-3 rounded-2xl border border-dashed border-stone-300 bg-white p-8 text-center">
            <div class="font-semibold">No matches yet</div>
            <p class="text-sm text-stone-500 mt-1">Run a scan to populate matches.</p>
            <button onclick="runPipeline()" class="mt-3 px-4 py-2 rounded-full bg-[#0F2A1A] text-white text-sm">Run scan now</button>
          </div>

          <div class="mt-8 flex items-center justify-between">
            <h2 class="text-[15px] font-semibold">All applications</h2>
            <div class="flex items-center gap-2">
              <button onclick="switchTab('tracker')" class="px-3 py-1.5 rounded-full border border-stone-200 bg-white text-xs">⧉ Open tracker</button>
              <button onclick="approveAll()" class="px-3 py-1.5 rounded-full bg-stone-200 text-stone-500 text-xs cursor-not-allowed">✓ Approve all</button>
            </div>
          </div>
          <div id="appsPreview" class="mt-3 rounded-2xl border border-stone-200 bg-white overflow-hidden">
            <div class="overflow-auto">
              <table class="w-full text-sm">
                <thead class="bg-stone-50 text-xs text-stone-500"><tr><th class="text-left px-4 py-3 font-medium">Company</th><th class="text-left px-4 py-3 font-medium">Role</th><th class="text-left px-4 py-3 font-medium">Status</th><th class="text-left px-4 py-3 font-medium">Score</th><th class="px-4 py-3"></th></tr></thead>
                <tbody id="appsPreviewBody" class="divide-y divide-stone-100"></tbody>
              </table>
            </div>
            <div id="emptyAppsPreview" class="p-6 text-center text-sm text-stone-500 hidden">No applications yet — approve a match above.</div>
          </div>
        </section>

        <!-- Browse pane -->
        <section id="pane-browse" class="hidden mt-6">
          <div class="rounded-2xl border border-stone-200 bg-white overflow-hidden">
            <div class="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
              <h3 class="text-sm font-semibold">Browse jobs</h3>
              <span class="text-xs text-stone-500"><span id="browseCount">0</span> ranked</span>
            </div>
            <div class="overflow-auto max-h-[560px]">
              <table class="w-full text-sm">
                <thead class="bg-stone-50 text-xs text-stone-500"><tr><th class="text-left px-4 py-3">Score</th><th class="text-left px-4 py-3">Company</th><th class="text-left px-4 py-3">Role</th><th class="text-left px-4 py-3">Location</th><th class="text-left px-4 py-3">Matched</th><th class="text-left px-4 py-3">Action</th></tr></thead>
                <tbody id="browseBody" class="divide-y divide-stone-100"></tbody>
              </table>
            </div>
          </div>
        </section>

        <!-- Auto Apply pane -->
        <section id="pane-auto" class="hidden mt-6">
          <div class="rounded-2xl border border-stone-200 bg-white p-6">
            <h3 class="text-lg font-semibold">Auto Apply</h3>
            <p class="mt-2 text-sm text-stone-600 leading-6">The agent watches company career pages (Greenhouse, Lever, Ashby, Workday), scores each role, tailors your resume + cover letter, and queues it for your approval. You approve → it submits through the real ATS and saves a receipt in Tracker.</p>
            <div class="mt-4 grid sm:grid-cols-3 gap-3 text-sm">
              <div class="rounded-xl border border-stone-200 p-4"><div class="font-semibold">1. Collect</div><div class="text-stone-500 mt-1">50k+ pages scanned each run</div></div>
              <div class="rounded-xl border border-stone-200 p-4"><div class="font-semibold">2. Tailor</div><div class="text-stone-500 mt-1">Per-role resume + diff</div></div>
              <div class="rounded-xl border border-stone-200 p-4"><div class="font-semibold">3. Apply</div><div class="text-stone-500 mt-1">You approve → receipt</div></div>
            </div>
            <button onclick="runPipeline()" class="mt-6 px-5 py-3 rounded-full bg-[#0F2A1A] text-white text-sm font-medium">Run Auto Apply now (dry-run)</button>
          </div>
        </section>

        <!-- Tracker pane -->
        <section id="pane-tracker" class="hidden mt-6">
          <div class="rounded-2xl border border-stone-200 bg-white overflow-hidden">
            <div class="px-4 py-3 border-b border-stone-100 flex items-center justify-between">
              <h3 class="text-sm font-semibold">Tracker — All applications</h3>
              <span class="text-xs text-stone-500"><span id="trackerCount">0</span> total</span>
            </div>
            <div class="overflow-auto">
              <table class="w-full text-sm">
                <thead class="bg-stone-50 text-xs text-stone-500"><tr><th class="text-left px-4 py-3">When</th><th class="text-left px-4 py-3">Company</th><th class="text-left px-4 py-3">Role</th><th class="text-left px-4 py-3">Score</th><th class="text-left px-4 py-3">Status</th><th class="text-left px-4 py-3">ATS</th><th class="px-4 py-3">Receipt</th></tr></thead>
                <tbody id="trackerBody" class="divide-y divide-stone-100"></tbody>
              </table>
            </div>
            <div id="emptyTracker" class="hidden p-8 text-center text-sm text-stone-500">No applications yet. Approve a match in Dashboard.</div>
          </div>
        </section>

        <!-- Networking pane -->
        <section id="pane-network" class="hidden mt-6">
          <div class="rounded-2xl border border-stone-200 bg-white p-6">
            <h3 class="text-lg font-semibold">Networking</h3>
            <p class="mt-2 text-sm text-stone-600">Recruiter outreach and referral helpers will appear here. For now, use Tracker receipts to follow up manually.</p>
          </div>
        </section>

        <!-- Profile pane -->
        <section id="pane-profile" class="hidden mt-6">
          <div class="grid lg:grid-cols-[1.2fr_0.8fr] gap-6">
            <div class="rounded-2xl border border-stone-200 bg-white p-6">
              <h3 class="text-sm font-bold tracking-widest">PROFILE & SETTINGS</h3>
              <p class="mt-1 text-xs text-stone-500">Stored locally in <code class="bg-stone-100 px-1 py-0.5 rounded text-xs">resumes/profile.yaml</code> — edit anytime.</p>
              <div class="mt-4 grid gap-3">
                <div class="grid sm:grid-cols-2 gap-3">
                  <div><label class="text-xs font-semibold text-stone-600">Full name</label><input id="s_name" class="mt-1 w-full h-9 rounded-xl border border-stone-200 px-3 text-sm"></div>
                  <div><label class="text-xs font-semibold text-stone-600">Email</label><input id="s_email" class="mt-1 w-full h-9 rounded-xl border border-stone-200 px-3 text-sm"></div>
                </div>
                <div class="grid sm:grid-cols-2 gap-3">
                  <div><label class="text-xs font-semibold text-stone-600">Phone</label><input id="s_phone" class="mt-1 w-full h-9 rounded-xl border border-stone-200 px-3 text-sm"></div>
                  <div><label class="text-xs font-semibold text-stone-600">Location</label><input id="s_location" class="mt-1 w-full h-9 rounded-xl border border-stone-200 px-3 text-sm"></div>
                </div>
                <label class="text-xs font-semibold text-stone-600">Target roles (comma separated — any role)</label><input id="s_roles" placeholder="Software Engineer, Product Manager, ..." class="h-9 rounded-xl border border-stone-200 px-3 text-sm">
                <label class="text-xs font-semibold text-stone-600">Skills (comma separated)</label><textarea id="s_skills" rows="3" class="w-full rounded-xl border border-stone-200 p-3 text-sm"></textarea>
                <label class="text-xs font-semibold text-stone-600">Work authorization</label><input id="s_auth" placeholder="US Citizen / H-1B / OPT" class="h-9 rounded-xl border border-stone-200 px-3 text-sm">
                <div class="flex items-center gap-3">
                  <button onclick="saveProfile()" class="px-5 py-2.5 rounded-full bg-[#0F2A1A] text-white text-sm font-medium">Save profile</button>
                  <span id="saveMsg" class="hidden text-sm text-emerald-600">Saved ✓</span>
                </div>
              </div>
            </div>
            <div class="space-y-4">
              <div class="rounded-2xl border border-stone-200 bg-white p-5">
                <h4 class="text-sm font-semibold">Resume</h4>
                <p class="mt-1 text-xs text-stone-500">Upload a .docx/.pdf to <code class="bg-stone-100 px-1 py-0.5 rounded">resumes/master_resume.docx</code> or paste below. The parser reads tables & text for any profession.</p>
                <div class="mt-3 h-40 rounded-xl border border-dashed border-stone-300 bg-stone-50 grid place-items-center text-sm text-stone-500">Drop resume here or edit profile.yaml</div>
                <div class="mt-3 text-xs text-stone-500">Current: <span id="profileMeta2" class="font-medium text-stone-700"></span></div>
              </div>
              <div class="rounded-2xl border border-stone-200 bg-[#0F2A1A] text-white p-5">
                <h4 class="text-sm font-semibold">Plan & usage</h4>
                <div class="mt-3 grid grid-cols-3 gap-2 text-center text-xs">
                  <div class="rounded-xl bg-white/10 p-3"><div class="font-bold text-lg">Free</div><div class="text-white/60">Template + dry-run</div></div>
                  <div class="rounded-xl bg-white text-[#0F2A1A] p-3"><div class="font-bold text-lg">Pro</div><div class="text-stone-500">Your OpenAI key</div></div>
                  <div class="rounded-xl bg-white/10 p-3"><div class="font-bold text-lg">Live</div><div class="text-white/60">Playwright</div></div>
                </div>
                <p class="mt-3 text-xs text-white/60">No subscription to this app. LLM cost ~$0.003/job only if you add a key. Dry-run is free forever.</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Research pane -->
        <section id="pane-research" class="hidden mt-6">
          <div class="rounded-2xl border border-stone-200 bg-white p-6">
            <h3 class="text-lg font-semibold">Research</h3>
            <p class="mt-2 text-sm text-stone-600">Company and role insights will appear here. Use Browse jobs filters to narrow by location, visa, experience.</p>
          </div>
        </section>

      </div>
    </div>
  </div>
</div>

<!-- Modal for preview/diff -->
<div id="modal" class="fixed inset-0 hidden z-50">
  <div class="absolute inset-0 bg-black/40 backdrop-blur-sm" onclick="closeModal()"></div>
  <div class="relative max-w-[860px] mx-auto mt-[6vh] rounded-2xl border border-stone-200 bg-white shadow-2xl overflow-hidden">
    <div class="px-5 py-4 flex items-center justify-between border-b border-stone-200">
      <div id="modalTitle" class="text-sm font-semibold">Preview</div>
      <button onclick="closeModal()" class="h-8 w-8 grid place-items-center rounded-full border border-stone-200">✕</button>
    </div>
    <div class="p-5 grid lg:grid-cols-2 gap-4 max-h-[70vh] overflow-auto">
      <div><div class="text-xs font-bold tracking-widest text-stone-500 mb-2">TAILORED RESUME</div><pre id="modalResume" class="whitespace-pre-wrap font-mono text-xs leading-5 p-3 rounded-xl bg-stone-50 border border-stone-200"></pre></div>
      <div><div class="text-xs font-bold tracking-widest text-stone-500 mb-2">COVER LETTER</div><pre id="modalCover" class="whitespace-pre-wrap text-xs leading-5 p-3 rounded-xl bg-stone-50 border border-stone-200"></pre></div>
      <div class="lg:col-span-2"><div class="text-xs font-bold tracking-widest text-stone-500 mb-2">DIFF vs ORIGINAL</div><pre id="modalDiff" class="whitespace-pre-wrap font-mono text-xs leading-5 p-3 rounded-xl bg-stone-50 border border-stone-200"></pre></div>
    </div>
  </div>
</div>

<div id="toast" class="fixed bottom-6 left-1/2 -translate-x-1/2 hidden z-50 px-4 py-3 rounded-full bg-[#0F2A1A] text-white text-sm font-medium shadow-xl">Done</div>

<script>
let QUEUE=[], RANKED=[], TRACKER=[], PROFILE={};

function switchTab(name){
  const panes=['dashboard','browse','auto','tracker','network','profile','research'];
  for(const p of panes){
    const el=document.getElementById('pane-'+p);
    if(el) el.classList.toggle('hidden', p!==name);
  }
  // update nav active state (simple)
  document.querySelectorAll('.nav-link').forEach(a=>{
    const is = a.getAttribute('href')==='#'+name || (name==='dashboard' && a.getAttribute('href')==='#dashboard');
    a.classList.toggle('bg-white', is);
    a.classList.toggle('border', is);
    a.classList.toggle('border-stone-200', is);
    a.classList.toggle('shadow-sm', is);
  });
  if(name==='browse') renderBrowse();
  if(name==='tracker') renderTracker();
  if(name==='profile') fillProfile();
  window.scrollTo({top:0, behavior:'smooth'});
}

const cardColors=['bg-[#D6EEFF]','bg-[#FFF4D6]','bg-[#E9E0FF]','bg-[#FFE2E2]','bg-[#D6F5E6]'];
function renderCards(){
  const grid=document.getElementById('jobCards');
  grid.innerHTML='';
  const q=document.getElementById('search').value.toLowerCase();
  const excl=document.getElementById('exclude').value.toLowerCase();
  let list=QUEUE;
  if(q) list=list.filter(j=> (j.role+' '+j.company+' '+j.description).toLowerCase().includes(q));
  if(excl) list=list.filter(j=> ! (j.role+' '+j.company).toLowerCase().includes(excl));
  document.getElementById('applyAllCount').textContent=list.length;
  if(list.length===0){ document.getElementById('emptyCards').classList.remove('hidden'); return; } else document.getElementById('emptyCards').classList.add('hidden');
  list.slice(0,5).forEach((j,idx)=>{
    const color=cardColors[idx % cardColors.length];
    const el=document.createElement('div');
    el.className=`rounded-2xl border border-stone-200 ${color} p-4 flex flex-col min-h-[220px]`;
    const loc=j.location||'Remote';
    const match=Math.round(j.match_score);
    el.innerHTML=`
      <div class="flex items-start justify-between gap-2">
        <div class="text-xs text-stone-600">${loc} <span class="ml-1 px-1.5 py-0.5 rounded-full bg-white border border-stone-200 text-[10px]">+4</span> <span class="text-stone-400">${timeAgo(j)}</span></div>
        <div class="match-ring bg-white border border-stone-200" style="--p:${match}"><span class="relative">${match}%<br><span class="text-[9px] tracking-widest text-stone-500">MATCH</span></span></div>
      </div>
      <div class="mt-6 flex-1">
        <div class="text-[15px] font-semibold leading-tight line-clamp-2">${j.role}</div>
        <div class="mt-1 text-xs text-stone-500">${j.company} • ${j.source}</div>
      </div>
      <div class="mt-4 flex items-center gap-2">
        <span class="h-6 w-6 rounded-lg bg-white border border-stone-200 grid place-items-center text-[11px] font-bold">${j.company[0]}</span>
        <span class="text-xs truncate">${j.company}</span>
        <span class="ml-auto flex gap-1.5">
          <button onclick="skip('${j.id}')" class="px-3 py-1.5 rounded-full bg-white border border-stone-200 text-xs font-medium">Pass</button>
          <button onclick="approve('${j.id}')" class="px-3.5 py-1.5 rounded-full bg-[#0F2A1A] text-white text-xs font-semibold">Apply</button>
        </span>
      </div>
      <div class="mt-2 text-center">
        <button onclick="openModal('${j.id}')" class="text-[11px] text-stone-500 hover:text-stone-700">Preview & diff →</button>
      </div>
    `;
    grid.appendChild(el);
  });
}
function timeAgo(j){ return j.date_posted ? j.date_posted.slice(0,10) : '5 days ago'; }

function renderBrowse(){
  const body=document.getElementById('browseBody'); if(!body) return;
  body.innerHTML='';
  document.getElementById('browseCount').textContent=RANKED.length;
  const q=document.getElementById('search').value.toLowerCase();
  let list=RANKED;
  if(q) list=list.filter(r=> (r.Role+' '+r.Company).toLowerCase().includes(q));
  for(const r of list.slice(0,50)){
    const tr=document.createElement('tr'); tr.className='hover:bg-stone-50';
    tr.innerHTML=`<td class="px-4 py-3 font-semibold">${r['Match Score']}%</td><td class="px-4 py-3">${r.Company}</td><td class="px-4 py-3">${r.Role}</td><td class="px-4 py-3 text-stone-500">${r.Location}</td><td class="px-4 py-3 text-xs">${r['Matched Skills']}</td><td class="px-4 py-3"><a href="${r.URL}" target="_blank" class="text-xs px-3 py-1 rounded-full bg-[#0F2A1A] text-white">Apply</a></td>`;
    body.appendChild(tr);
  }
}
function renderAppsPreview(){
  const body=document.getElementById('appsPreviewBody'); if(!body) return;
  body.innerHTML='';
  const apps=TRACKER.slice(0,5);
  if(apps.length===0){ document.getElementById('emptyAppsPreview').classList.remove('hidden'); return; } else document.getElementById('emptyAppsPreview').classList.add('hidden');
  for(const a of apps){
    const tr=document.createElement('tr');
    tr.innerHTML=`<td class="px-4 py-3">${a.company||a.Company}</td><td class="px-4 py-3">${a.role||a.Role}</td><td class="px-4 py-3"><span class="px-2 py-1 rounded-full bg-stone-100 border border-stone-200 text-xs">${a.status}</span></td><td class="px-4 py-3">${a.match_score||''}</td><td class="px-4 py-3"><a href="/receipt/${a.id}" target="_blank" class="text-xs text-stone-600 hover:underline">receipt</a></td>`;
    body.appendChild(tr);
  }
}
function renderTracker(){
  const body=document.getElementById('trackerBody'); if(!body) return;
  body.innerHTML='';
  document.getElementById('trackerCount').textContent=TRACKER.length;
  document.getElementById('emptyTracker').classList.toggle('hidden', TRACKER.length!==0);
  for(const a of TRACKER){
    const tr=document.createElement('tr'); tr.className='hover:bg-stone-50';
    const when=(a.applied_at||'').slice(0,19).replace('T',' ');
    tr.innerHTML=`<td class="px-4 py-3 font-mono text-xs">${when}</td><td class="px-4 py-3">${a.company||a.Company}</td><td class="px-4 py-3">${a.role||a.Role}</td><td class="px-4 py-3">${a.match_score||''}</td><td class="px-4 py-3"><span class="px-2 py-1 rounded-full bg-stone-100 border text-xs">${a.status}</span></td><td class="px-4 py-3 text-xs">${a.ats||''}</td><td class="px-4 py-3"><a href="/receipt/${a.id}" target="_blank" class="text-xs underline">receipt</a></td>`;
    body.appendChild(tr);
  }
}
function openModal(id){
  const j=QUEUE.find(x=>x.id===id); if(!j) return;
  document.getElementById('modalTitle').textContent=j.role+' at '+j.company;
  document.getElementById('modalResume').textContent=j.resume_preview||'';
  document.getElementById('modalCover').textContent=j.cover_preview||'';
  document.getElementById('modalDiff').textContent=j.diff||'';
  document.getElementById('modal').classList.remove('hidden');
}
function closeModal(){ document.getElementById('modal').classList.add('hidden'); }
function showToast(msg){ const el=document.getElementById('toast'); el.textContent=msg; el.classList.remove('hidden'); setTimeout(()=>el.classList.add('hidden'),2200); }
async function loadAll(){
  const [q,r,s,t,p]=await Promise.all([
    fetch('/api/queue').then(x=>x.json()).catch(()=>[]),
    fetch('/api/ranked').then(x=>x.json()).catch(()=>[]),
    fetch('/api/stats').then(x=>x.json()).catch(()=>({})),
    fetch('/api/applications').then(x=>x.json()).catch(()=>[]),
    fetch('/api/profile').then(x=>x.json()).catch(()=>({}))
  ]);
  QUEUE=q; RANKED=r; TRACKER=t; PROFILE=p||{};
  document.getElementById('leftCount').textContent=QUEUE.length;
  renderCards(); renderBrowse(); renderAppsPreview(); renderTracker();
  // update profile header
  const nameEl=document.querySelector('#profileHeaderName');
  if(nameEl) nameEl.textContent=PROFILE.name||'';
}
async function approve(id){
  const btn=event?.target; if(btn){ btn.textContent='Applying…'; btn.disabled=true; }
  try{ const r=await fetch('/approve/'+id,{method:'POST'}); if(!r.ok) throw new Error(); showToast('Applied ✓ — receipt saved'); } catch(e){ showToast('Failed'); }
  setTimeout(loadAll,800);
}
async function skip(id){
  await fetch('/skip/'+id,{method:'POST'}); showToast('Passed'); setTimeout(loadAll,500);
}
async function approveAll(){
  if(!confirm('Apply to all '+QUEUE.length+' top matches (dry-run)?')) return;
  showToast('Applying to all…');
  await fetch('/approve_all',{method:'POST'}); setTimeout(loadAll,1200);
}
function triggerApplyTop(){ if(QUEUE.length) approve(QUEUE[0].id); else showToast('No top matches — run scan'); }
async function runPipeline(){
  showToast('Scan started — collecting career pages…');
  try{ const r=await fetch('/api/run',{method:'POST'}); const j=await r.json(); showToast(j.msg||'Queued'); } catch(e){ showToast('Scan failed'); }
  let tries=0; const poll=setInterval(async()=>{ await loadAll(); tries++; if(QUEUE.length>0 || tries>10){ clearInterval(poll); showToast('Scan done ✓'); } },2500);
}
async function saveProfile(){
  const body={ name: document.getElementById('s_name').value, email: document.getElementById('s_email').value, phone: document.getElementById('s_phone').value, location: document.getElementById('s_location').value, target_roles: document.getElementById('s_roles').value, skills: document.getElementById('s_skills').value };
  await fetch('/api/profile',{method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify(body)});
  document.getElementById('saveMsg').classList.remove('hidden'); setTimeout(()=>document.getElementById('saveMsg').classList.add('hidden'),2000); loadAll();
}
function fillProfile(){
  document.getElementById('s_name').value=PROFILE.name||'';
  document.getElementById('s_email').value=PROFILE.email||'';
  document.getElementById('s_phone').value=PROFILE.phone||'';
  document.getElementById('s_location').value=PROFILE.location||'';
  document.getElementById('s_roles').value=(PROFILE.target_roles||[]).join(', ');
  document.getElementById('s_skills').value=(PROFILE.skills||[]).join(', ');
  document.getElementById('profileMeta2').textContent=(PROFILE.skills||[]).slice(0,6).join(', ');
}
function fillChat(txt){ document.getElementById('chatInput').value=txt; }
function sendChat(){
  const v=document.getElementById('chatInput').value.trim();
  if(!v) return;
  if(v.toLowerCase().includes('top matches')) triggerApplyTop();
  else if(v.toLowerCase().includes('applications')) switchTab('tracker');
  else if(v.toLowerCase().includes('recommendation')) switchTab('browse');
  else showToast('Assistant: try "Apply to my top matches" or "Where are my applications?"');
  document.getElementById('chatInput').value='';
}
document.getElementById('search').addEventListener('input', ()=>{ renderCards(); renderBrowse(); });
document.getElementById('exclude').addEventListener('input', renderCards);
loadAll();
setInterval(loadAll, 5000);
</script>
</body>
</html>
"""

RANKED_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Ranked</title>
<style>body{font-family:Inter,system-ui,sans-serif;background:#F8F7F3;color:#0f172a;margin:0}header{padding:16px 24px;border-bottom:1px solid #e7e5e4} .container{max-width:1100px;margin:0 auto;padding:24px} table{width:100%;border-collapse:collapse;font-size:13px} th,td{padding:8px;border-bottom:1px solid #e7e5e4} th{color:#78716c;font-size:11px;text-transform:uppercase} a{color:#0F2A1A}</style>
</head><body><header><h1>Ranked Jobs</h1><a href="/" style="color:#0F2A1A">← Back</a></header><div class="container"><table><tr><th>Score</th><th>Company</th><th>Role</th><th>Location</th><th>Matched</th><th>Decision</th><th>Link</th></tr>{% for r in rows %}<tr><td>{{r['Match Score']}}%</td><td>{{r.Company}}</td><td>{{r.Role}}</td><td>{{r.Location}}</td><td style="font-size:11px">{{r['Matched Skills']}}</td><td>{{r.Decision}}</td><td><a href="{{r.URL}}" target="_blank">open</a></td></tr>{% endfor %}</table></div></body></html>"""

TRACKER_HTML = """<!doctype html><html><head><meta charset="utf-8"><title>Tracker</title>
<style>body{font-family:Inter,system-ui,sans-serif;background:#F8F7F3;color:#0f172a;margin:0}header{padding:16px 24px;border-bottom:1px solid #e7e5e4} .container{max-width:1100px;margin:0 auto;padding:24px} table{width:100%;border-collapse:collapse;font-size:13px} th,td{padding:8px;border-bottom:1px solid #e7e5e4} th{color:#78716c;font-size:11px;text-transform:uppercase} a{color:#0F2A1A}</style>
</head><body><header><h1>Tracker</h1><a href="/" style="color:#0F2A1A">← Back</a></header><div class="container"><table><tr><th>When</th><th>Company</th><th>Role</th><th>Score</th><th>Status</th><th>ATS</th><th>Receipt</th></tr>{% for a in apps %}<tr><td>{{a.applied_at[:19]}}</td><td>{{a.company or a.Company}}</td><td>{{a.role or a.Role}}</td><td>{{a.match_score or a['match_score']}}</td><td>{{a.status}}</td><td>{{a.ats or a.ATS}}</td><td>{% if a.receipt_path %}<a href="/receipt/{{a.id}}">view</a>{% else %}-{% endif %}</td></tr>{% endfor %}</table>{% if not apps %}<p style="color:#78716c">No applications yet.</p>{% endif %}</div></body></html>"""

def _load_queue():
    qp = resolve_path("output/approval_queue.json")
    if not qp.exists():
        return []
    try:
        return json.loads(qp.read_text(encoding="utf-8"))
    except Exception:
        return []

def _load_ranked():
    p = resolve_path("output/ranked_jobs.csv")
    if not p.exists():
        return []
    try:
        df = pd.read_csv(p).fillna("")
        return df.to_dict(orient="records")
    except:
        return []

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return HTMLResponse(DASH_HTML)

@app.get("/ranked", response_class=HTMLResponse)
def ranked_view():
    from jinja2 import Template
    rows = _load_ranked()
    return HTMLResponse(Template(RANKED_HTML).render(rows=rows))

@app.get("/applications", response_class=HTMLResponse)
def applications_view():
    from jinja2 import Template
    apps = load_applications()
    return HTMLResponse(Template(TRACKER_HTML).render(apps=apps))

@app.get("/api/queue")
def api_queue():
    return JSONResponse(_load_queue())

@app.get("/api/ranked")
def api_ranked():
    return JSONResponse(_load_ranked())

@app.get("/api/applications")
def api_applications():
    return JSONResponse(load_applications())

@app.get("/api/stats")
def api_stats():
    return JSONResponse({"queue": len(_load_queue()), "ranked": len(_load_ranked()), "tracker": get_stats()})

@app.get("/api/profile")
def api_get_profile():
    p = load_profile()
    cfg = get_settings()
    return JSONResponse({
        "name": p.name,
        "email": p.email,
        "phone": p.phone,
        "location": p.location,
        "linkedin": p.linkedin,
        "github": p.github,
        "skills": p.skills,
        "target_roles": cfg.get("preferences", {}).get("target_roles", []),
        "raw": p.raw_text[:600],
    })

@app.post("/api/profile")
async def api_save_profile(request: Request):
    data = await request.json()
    prof_path = resolve_path("resumes/profile.yaml")
    ensure_dirs()
    try:
        current = yaml.safe_load(prof_path.read_text(encoding="utf-8")) if prof_path.exists() else {}
    except:
        current = {}
    if "name" in data and data["name"]:
        current["name"] = data["name"]
    if "email" in data:
        current["email"] = data["email"]
    if "phone" in data:
        current["phone"] = data["phone"]
    if "location" in data:
        current["location"] = data["location"]
    if "skills" in data and data["skills"]:
        if isinstance(data["skills"], str):
            current["skills"] = [s.strip() for s in data["skills"].split(",") if s.strip()]
        else:
            current["skills"] = data["skills"]
    prof_path.write_text(yaml.safe_dump(current, sort_keys=False), encoding="utf-8")
    if "target_roles" in data and data["target_roles"]:
        cfg_path = resolve_path("config/settings.yaml")
        cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) if cfg_path.exists() else {}
        cfg.setdefault("preferences", {})["target_roles"] = [s.strip() for s in data["target_roles"].split(",") if s.strip()]
        cfg_path.write_text(yaml.safe_dump(cfg, sort_keys=False), encoding="utf-8")
        import src.config as cfgmod
        cfgmod._settings_cache = None
    return JSONResponse({"ok": True})

@app.post("/api/run")
def api_run(background_tasks: BackgroundTasks):
    def do_run():
        from ..pipeline import run_once
        class Args:
            skip_collect=False
            collect_only=False
            tailor_top=8
            max_per_source=12
            max_total=80
            max_apply=25
            apply=True
            auto_approve=False
            dry_run=False
            live=False
            no_threads=False
            once=True
            watch=0
        run_once(Args())
    background_tasks.add_task(do_run)
    return JSONResponse({"queued": True, "msg": "Scan started — will appear in ~12s"})

@app.post("/approve/{job_id}")
def approve_one(job_id: str, background_tasks: BackgroundTasks):
    queue = _load_queue()
    job = next((j for j in queue if j["id"] == job_id), None)
    if not job:
        return JSONResponse({"ok": False}, status_code=404)
    def do_apply():
        from ..models import ScoredJob
        from ..resume_parser import load_profile
        from ..apply.applier import dry_run_apply
        profile = load_profile()
        sj = ScoredJob(id=job["id"], company=job["company"], role=job["role"], location=job["location"], url=job["url"], description=job.get("resume_preview",""), source=job.get("source","generic"), match_score=job["match_score"], matched_skills=job["matched_skills"], missing_skills=job["missing_skills"], decision=job["decision"], fit_label="Medium")
        dry_run_apply(sj, profile)
        new_q = [q for q in _load_queue() if q["id"] != job_id]
        resolve_path("output/approval_queue.json").write_text(json.dumps(new_q, indent=2), encoding="utf-8")
    background_tasks.add_task(do_apply)
    return JSONResponse({"ok": True, "approved": job_id})

@app.post("/skip/{job_id}")
def skip_one(job_id: str):
    queue = _load_queue()
    new_q = [q for q in queue if q["id"] != job_id]
    resolve_path("output/approval_queue.json").write_text(json.dumps(new_q, indent=2), encoding="utf-8")
    from ..models import ScoredJob
    from ..apply.tracker import record_application
    job = next((j for j in queue if j["id"] == job_id), None)
    if job:
        sj = ScoredJob(id=job["id"], company=job["company"], role=job["role"], location=job["location"], url=job["url"], description="", source=job["source"], match_score=job["match_score"], matched_skills=job["matched_skills"], missing_skills=job["missing_skills"])
        record_application(sj, status="skipped")
    return JSONResponse({"ok": True})

@app.post("/approve_all")
def approve_all(background_tasks: BackgroundTasks):
    queue = _load_queue()
    def do_all():
        from ..models import ScoredJob
        from ..resume_parser import load_profile
        from ..apply.applier import dry_run_apply
        profile = load_profile()
        for job in queue:
            sj = ScoredJob(id=job["id"], company=job["company"], role=job["role"], location=job["location"], url=job["url"], description=job.get("resume_preview",""), source=job.get("source","generic"), match_score=job["match_score"], matched_skills=job["matched_skills"], missing_skills=job["missing_skills"], decision=job["decision"], fit_label="Medium")
            dry_run_apply(sj, profile)
            time.sleep(0.3)
        resolve_path("output/approval_queue.json").write_text("[]", encoding="utf-8")
    background_tasks.add_task(do_all)
    return JSONResponse({"ok": True, "count": len(queue)})

@app.get("/receipt/{job_id}")
def receipt(job_id: str):
    rd = resolve_path("output/receipts")
    matches = list(rd.glob(f"*{job_id}*"))
    if not matches:
        matches = list(rd.glob("*.json"))
        for m in matches:
            try:
                if job_id in m.read_text():
                    return JSONResponse(json.loads(m.read_text()))
            except: pass
        return JSONResponse({"error":"not found"}, status_code=404)
    try:
        return JSONResponse(json.loads(matches[0].read_text()))
    except Exception as e:
        return JSONResponse({"error":str(e)}, status_code=500)

def run():
    import uvicorn
    cfg = get_settings()
    host = cfg.get("dashboard",{}).get("host","0.0.0.0")
    port = int(cfg.get("dashboard",{}).get("port",8000))
    print(f"Starting dashboard at http://{host}:{port}  (also: http://localhost:{port})")
    uvicorn.run(app, host=host, port=port)

if __name__ == "__main__":
    run()
