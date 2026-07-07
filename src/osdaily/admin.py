from __future__ import annotations

import json
import os
import threading
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from . import __version__
from .enrichment import build_mode, cache_key, enrich_with_llm, resolve_provider
from .models import NewsItem
from .report import write_report
from .quality import build_quality_report
from .runner import RunOptions, run_pipeline
from .scheduler import SchedulerState, start_daily_scheduler
from .storage import Store


HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>开源日报编辑台</title>
  <style>
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --ink: #1f2937;
      --muted: #667085;
      --line: #d9dee7;
      --blue: #2563eb;
      --green: #15803d;
      --red: #b42318;
      --amber: #b7791f;
    }
    * { box-sizing: border-box; }
    [hidden] { display: none !important; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--ink);
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      font-size: 14px;
      letter-spacing: 0;
    }
    header {
      display: grid;
      grid-template-columns: minmax(220px, 1fr) auto;
      gap: 16px;
      align-items: center;
      padding: 16px 24px;
      border-bottom: 1px solid var(--line);
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 2;
    }
    h1 {
      margin: 0;
      font-size: 20px;
      line-height: 1.2;
      font-weight: 700;
    }
    .toolbar {
      display: flex;
      gap: 8px;
      align-items: center;
      flex-wrap: wrap;
      justify-content: flex-end;
    }
    input, select, textarea {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      padding: 8px 10px;
      font: inherit;
      min-width: 0;
    }
    input[type="search"] { width: min(360px, 42vw); }
    input[type="number"] { width: 78px; }
    button {
      border: 1px solid var(--line);
      background: #fff;
      color: var(--ink);
      border-radius: 6px;
      padding: 8px 10px;
      font: inherit;
      cursor: pointer;
    }
    button.primary {
      background: var(--blue);
      border-color: var(--blue);
      color: #fff;
    }
    button:disabled { opacity: .55; cursor: not-allowed; }
    main {
      display: grid;
      grid-template-columns: minmax(320px, 42%) 1fr;
      min-height: calc(100vh - 65px);
    }
    aside {
      border-right: 1px solid var(--line);
      background: #fff;
      overflow: auto;
      max-height: calc(100vh - 65px);
    }
    .stats {
      display: flex;
      gap: 12px;
      padding: 12px 16px;
      color: var(--muted);
      border-bottom: 1px solid var(--line);
      flex-wrap: wrap;
    }
    .run-panel {
      display: grid;
      gap: 6px;
      padding: 12px 16px;
      color: var(--muted);
      border-bottom: 1px solid var(--line);
      background: #fbfcfe;
      line-height: 1.45;
    }
    .run-panel strong { color: var(--ink); }
    .reports {
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .reports a {
      color: var(--blue);
      text-decoration: none;
      border-bottom: 1px solid transparent;
    }
    .reports a:hover { border-bottom-color: var(--blue); }
    .quality-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 6px 12px;
    }
    .list { display: grid; }
    .row {
      display: grid;
      grid-template-columns: 28px 1fr;
      gap: 8px;
      padding: 12px 16px;
      border-bottom: 1px solid var(--line);
      cursor: pointer;
    }
    .row:hover, .row.active { background: #eef4ff; }
    .row-title {
      font-weight: 650;
      line-height: 1.35;
      overflow-wrap: anywhere;
    }
    .meta {
      color: var(--muted);
      font-size: 12px;
      margin-top: 6px;
      display: flex;
      gap: 8px;
      flex-wrap: wrap;
    }
    .tag {
      background: #eef2f6;
      border: 1px solid #d8dee8;
      border-radius: 999px;
      padding: 1px 7px;
    }
    .tag.accepted { background: #eaf7ee; border-color: #b8e0c3; color: var(--green); }
    .tag.rejected { background: #fff1f0; border-color: #f0c4bd; color: var(--red); }
    .tag.candidate { background: #fff8e6; border-color: #eed08a; color: var(--amber); }
    section.editor {
      padding: 18px 24px 28px;
      overflow: auto;
      max-height: calc(100vh - 65px);
    }
    .empty {
      color: var(--muted);
      padding: 40px 0;
    }
    .form {
      display: grid;
      gap: 14px;
      max-width: 920px;
    }
    label {
      display: grid;
      gap: 6px;
      font-weight: 650;
    }
    textarea { min-height: 160px; resize: vertical; line-height: 1.5; }
    .title-input { font-size: 18px; font-weight: 700; }
    .url {
      color: var(--blue);
      overflow-wrap: anywhere;
      text-decoration: none;
    }
    .status {
      min-height: 20px;
      color: var(--green);
    }
    .status.error { color: var(--red); }
    .preview {
      border-top: 1px solid var(--line);
      margin-top: 12px;
      padding-top: 12px;
      color: var(--muted);
      line-height: 1.55;
    }
    body { background: #eef1f5; }
    header {
      grid-template-columns: minmax(220px, auto) 1fr;
      box-shadow: 0 1px 0 rgba(31, 41, 55, .04);
    }
    .toolbar {
      justify-content: flex-end;
      row-gap: 10px;
    }
    input:focus, select:focus, textarea:focus {
      outline: 2px solid rgba(37, 99, 235, .18);
      border-color: #8fb4ff;
    }
    button:hover { background: #f8fafc; border-color: #b7c0ce; }
    button.primary:hover { background: #1d4ed8; border-color: #1d4ed8; }
    main {
      grid-template-columns: minmax(360px, 40%) minmax(520px, 1fr);
      background: #f6f7f9;
    }
    aside { background: #fbfcfe; }
    .stats {
      gap: 8px;
      padding: 14px 16px;
      background: #fff;
      color: var(--ink);
    }
    .stats span {
      display: inline-flex;
      align-items: center;
      min-height: 26px;
      padding: 3px 8px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      color: var(--muted);
      font-size: 12px;
      white-space: nowrap;
    }
    .run-panel {
      padding: 10px 16px;
      background: #fbfcfe;
      font-size: 12px;
    }
    .run-panel + .run-panel { background: #fff; }
    .metric-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 8px;
    }
    .metric {
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
      padding: 8px;
      min-width: 0;
    }
    .metric b {
      display: block;
      color: var(--ink);
      font-size: 16px;
      line-height: 1.2;
      overflow-wrap: anywhere;
    }
    .metric span {
      display: block;
      margin-top: 3px;
      color: var(--muted);
      font-size: 12px;
    }
    .row {
      grid-template-columns: 24px 1fr;
      padding: 13px 16px;
      background: #fff;
    }
    .row-title { font-size: 14px; }
    .row-summary {
      margin-top: 6px;
      color: var(--muted);
      line-height: 1.45;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }
    .meta { gap: 6px; }
    .tag { line-height: 1.5; }
    section.editor {
      background: #fff;
      padding: 22px 28px 32px;
    }
    .form {
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 16px;
      max-width: 980px;
    }
    .form label:first-child,
    .form label:nth-child(2),
    .form label:nth-child(7),
    .url,
    .form .toolbar,
    .status,
    .preview {
      grid-column: 1 / -1;
    }
    label { color: #344054; }
    textarea { min-height: 180px; }
    #editorNote { min-height: 92px; }
    .preview {
      border: 1px solid var(--line);
      border-radius: 8px;
      padding: 14px;
      background: #fbfcfe;
    }
    .empty {
      display: grid;
      place-items: center;
      min-height: 320px;
      border: 1px dashed #c9d2df;
      border-radius: 8px;
      background: #fbfcfe;
    }
    @media (max-width: 860px) {
      header { grid-template-columns: 1fr; }
      .toolbar { justify-content: flex-start; }
      input[type="search"] { width: 100%; }
      main { grid-template-columns: 1fr; }
      aside, section.editor { max-height: none; }
      aside { border-right: 0; }
      .metric-grid, .form { grid-template-columns: 1fr; }
    }
    :root {
      --bg: #08090c;
      --panel: rgba(18, 19, 24, .86);
      --ink: #f5f7fb;
      --muted: #9aa4b2;
      --line: rgba(255, 255, 255, .11);
      --blue: #7c5cff;
      --green: #40c978;
      --red: #ff6b6b;
      --amber: #f7ba4b;
    }
    body {
      background:
        radial-gradient(circle at 22% 12%, rgba(124, 92, 255, .24), transparent 34%),
        radial-gradient(circle at 76% 0%, rgba(38, 210, 196, .16), transparent 32%),
        linear-gradient(135deg, #08090c 0%, #11131a 58%, #0a0b0f 100%);
      color: var(--ink);
    }
    header {
      background: rgba(10, 11, 15, .78);
      border-bottom-color: var(--line);
      backdrop-filter: blur(18px);
      box-shadow: 0 16px 40px rgba(0, 0, 0, .28);
    }
    h1 {
      font-size: 22px;
      display: flex;
      align-items: center;
      gap: 10px;
    }
    h1::before {
      content: "";
      width: 12px;
      height: 12px;
      border-radius: 50%;
      background: linear-gradient(135deg, #8b5cf6, #22d3ee);
      box-shadow: 0 0 22px rgba(124, 92, 255, .95);
    }
    .version {
      color: var(--muted);
      border: 1px solid var(--line);
      border-radius: 999px;
      padding: 2px 7px;
      font-size: 12px;
      font-weight: 700;
    }
    input, select, textarea, button {
      background: rgba(255, 255, 255, .06);
      color: var(--ink);
      border-color: var(--line);
      border-radius: 8px;
    }
    input::placeholder, textarea::placeholder { color: #70798a; }
    select option { color: #111827; background: #fff; }
    button {
      background: rgba(255, 255, 255, .07);
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, .06);
    }
    button:hover {
      background: rgba(255, 255, 255, .12);
      border-color: rgba(255, 255, 255, .22);
    }
    button.primary {
      background: linear-gradient(135deg, #7c5cff, #3b82f6);
      border-color: rgba(255, 255, 255, .18);
      box-shadow: 0 12px 30px rgba(79, 70, 229, .32);
    }
    button.primary:hover {
      background: linear-gradient(135deg, #8b6cff, #4f8df7);
      border-color: rgba(255, 255, 255, .3);
    }
    main {
      gap: 1px;
      padding: 1px;
      background: rgba(255, 255, 255, .08);
    }
    aside, section.editor {
      background: rgba(12, 13, 18, .72);
      backdrop-filter: blur(20px);
    }
    .stats, .run-panel, .run-panel + .run-panel, .row, .metric, .preview, .empty {
      background: var(--panel);
      border-color: var(--line);
    }
    .stats span, .tag {
      background: rgba(255, 255, 255, .06);
      border-color: var(--line);
      color: var(--muted);
    }
    .metric b, label, .row-title, .run-panel strong { color: var(--ink); }
    .metric {
      border-radius: 8px;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, .05);
    }
    .row {
      border-bottom-color: rgba(255, 255, 255, .08);
      transition: background .16s ease, border-color .16s ease;
    }
    .row:hover, .row.active {
      background: rgba(124, 92, 255, .15);
      border-color: rgba(124, 92, 255, .35);
    }
    .row.active { box-shadow: inset 3px 0 0 #7c5cff; }
    .tag.accepted { background: rgba(64, 201, 120, .12); border-color: rgba(64, 201, 120, .35); color: #7ee2a3; }
    .tag.rejected { background: rgba(255, 107, 107, .13); border-color: rgba(255, 107, 107, .35); color: #ff9a9a; }
    .tag.candidate { background: rgba(247, 186, 75, .13); border-color: rgba(247, 186, 75, .35); color: #ffd37a; }
    .toolbar label.inline {
      display: inline-flex;
      grid-auto-flow: column;
      align-items: center;
      gap: 7px;
      margin: 0 2px;
      color: var(--muted);
      font-weight: 600;
      white-space: nowrap;
    }
    .toolbar label.inline input { width: 16px; height: 16px; }
    .url { color: #93c5fd; }
    .status { color: #7ee2a3; }
    .status.error { color: #ff9a9a; }
    .progress-wrap {
      display: grid;
      gap: 7px;
      margin-top: 8px;
    }
    .progress-track {
      height: 8px;
      overflow: hidden;
      border-radius: 999px;
      background: rgba(255, 255, 255, .08);
      border: 1px solid rgba(255, 255, 255, .1);
    }
    .progress-fill {
      width: 0%;
      height: 100%;
      border-radius: inherit;
      background: linear-gradient(90deg, #22d3ee, #7c5cff, #3b82f6);
      box-shadow: 0 0 18px rgba(124, 92, 255, .55);
      transition: width .35s ease;
    }
    .progress-meta {
      display: flex;
      justify-content: space-between;
      gap: 10px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.35;
    }
    .progress-meta span {
      overflow-wrap: anywhere;
    }
  </style>
</head>
<body>
  <header>
    <h1>开源日报编辑台</h1>
    <div class="toolbar">
      <input id="q" type="search" placeholder="搜索标题、摘要、来源、标签">
      <select id="category"></select>
      <select id="curationFilter">
        <option value="">全部状态</option>
        <option value="accepted">采用</option>
        <option value="candidate">备选</option>
        <option value="rejected">舍弃</option>
      </select>
      <button id="selectAll">全选</button>
      <button id="selectNone">清空</button>
      <input id="runDays" type="number" min="1" max="14" value="1" title="回溯天数">
      <button id="runNow">重新采集</button>
      <button class="primary" id="export">导出 Markdown</button>
    </div>
  </header>
  <main>
    <aside>
      <div class="stats">
        <span id="total">0 条</span>
        <span id="checked">0 已选</span>
        <span id="saved"></span>
      </div>
      <div class="run-panel" id="runPanel">正在读取运行状态...</div>
      <div class="run-panel" id="schedulePanel">正在读取调度状态...</div>
      <div class="run-panel">
        <strong>最近日报：</strong>
        <div class="reports" id="reports">正在读取...</div>
      </div>
      <div class="run-panel">
        <strong>7 天质量：</strong>
        <div class="quality-grid" id="quality">正在读取...</div>
      </div>
      <div class="list" id="list"></div>
    </aside>
    <section class="editor">
      <div class="empty" id="empty">选择左侧条目开始编辑。</div>
      <form class="form" id="form" hidden>
        <label>标题
          <input class="title-input" id="title">
        </label>
        <label>摘要
          <textarea id="summary"></textarea>
        </label>
        <label>分类
          <input id="editCategory">
        </label>
        <label>标签，用逗号分隔
          <input id="tags">
        </label>
        <label>采纳状态
          <select id="curationStatus">
            <option value="accepted">采用</option>
            <option value="candidate">备选</option>
            <option value="rejected">舍弃</option>
          </select>
        </label>
        <label>编辑备注
          <textarea id="editorNote" style="min-height: 84px"></textarea>
        </label>
        <a class="url" id="url" target="_blank" rel="noreferrer"></a>
        <div class="toolbar">
          <button class="primary" type="submit">保存修改</button>
          <button type="button" id="togglePick">切换采用</button>
        </div>
        <div class="status" id="status"></div>
        <div class="preview" id="preview"></div>
      </form>
    </section>
  </main>
  <script>
    const state = { items: [], current: null, selected: new Set() };
    const $ = (id) => document.getElementById(id);

    async function loadItems() {
      const res = await fetch(apiUrl('/api/items?limit=500'));
      state.items = await res.json();
      state.selected.clear();
      state.items.filter(item => (item.curation_status || 'candidate') !== 'rejected').forEach(item => state.selected.add(item.id));
      renderCategories();
      renderList();
    }

    async function loadSummary() {
      const [summaryRes, stateRes, scheduleRes] = await Promise.all([
        fetch(apiUrl('/api/summary')),
        fetch(apiUrl('/api/run-state')),
        fetch(apiUrl('/api/scheduler'))
      ]);
      const summary = await summaryRes.json();
      const runState = await stateRes.json();
      const scheduler = await scheduleRes.json();
      renderRunPanel(summary, runState);
      renderSchedulePanel(scheduler);
    }

    async function loadReports() {
      const res = await fetch(apiUrl('/api/reports'));
      const reports = await res.json();
      $('reports').innerHTML = reports.length
        ? reports.map(r => `<a target="_blank" rel="noreferrer" href="${apiUrl('/reports/' + encodeURIComponent(r.name))}">${escapeHtml(r.name)}</a>`).join('')
        : '暂无';
    }

    async function loadQuality() {
      const res = await fetch(apiUrl('/api/quality?days=7'));
      const quality = await res.json();
      const failed = (quality.failed_sources || []).slice(0, 3).map(s => `${s.name}(${s.failures})`).join('，') || '无';
      $('quality').innerHTML = `
        <span>运行：${escapeHtml(quality.runs ?? 0)}</span>
        <span>成功：${escapeHtml(Math.round((quality.success_rate ?? 0) * 100))}%</span>
        <span>均值：${escapeHtml(quality.average_items ?? 0)}</span>
        <span>告警：${escapeHtml(quality.total_warnings ?? 0)}</span>
        <span style="grid-column: 1 / -1">失败源：${escapeHtml(failed)}</span>
      `;
    }

    async function loadVersion() {
      try {
        const res = await fetch(apiUrl('/api/version'));
        if (!res.ok) return;
        const data = await res.json();
        const title = document.querySelector('h1');
        if (title && data.version && !title.querySelector('.version')) {
          const badge = document.createElement('span');
          badge.className = 'version';
          badge.textContent = `v${data.version}`;
          title.appendChild(badge);
        }
      } catch (error) {
        return;
      }
    }

    function renderRunPanel(summary, runState) {
      const running = runState.running ? '运行中' : '空闲';
      const last = summary.generated_at || '暂无';
      const count = summary.report_items ?? 0;
      const warnings = (summary.warnings || []).length ? summary.warnings.join('；') : '无';
      const failed = Object.values(summary.sources || {}).filter(s => !s.ok).map(s => s.name).join('，') || '无';
      $('runPanel').innerHTML = `
        <div class="metric-grid">
          <div class="metric"><b>${escapeHtml(running)}</b><span>运行状态</span></div>
          <div class="metric"><b>${escapeHtml(count)}</b><span>最近条目</span></div>
          <div class="metric"><b>${escapeHtml(failed === '无' ? 0 : failed.split('，').length)}</b><span>失败源</span></div>
        </div>
        <div><strong>最近生成：</strong>${escapeHtml(last)}</div>
        <div><strong>告警：</strong>${escapeHtml(warnings)}${runState.error ? `；${escapeHtml(runState.error)}` : ''}</div>
      `;
    }

    function renderSchedulePanel(scheduler) {
      const enabled = scheduler.enabled ? '已开启' : '未开启';
      const running = scheduler.running ? '运行中' : '空闲';
      const next = scheduler.next_run_hint || '无';
      const last = scheduler.last_finished_at || '暂无';
      const error = scheduler.last_error || '无';
      $('schedulePanel').innerHTML = `
        <div><strong>定时调度：</strong>${escapeHtml(enabled)} | <strong>时间：</strong>${escapeHtml(scheduler.schedule_time || '06:00')} | <strong>状态：</strong>${escapeHtml(running)}</div>
        <div><strong>下次：</strong>${escapeHtml(next)}</div>
        <div><strong>上次完成：</strong>${escapeHtml(last)} | <strong>错误：</strong>${escapeHtml(error)}</div>
      `;
    }

    function renderCategories() {
      const cats = [...new Set(state.items.map(i => i.category || '综合'))].sort();
      $('category').innerHTML = '<option value="">全部分类</option>' + cats.map(c => `<option>${escapeHtml(c)}</option>`).join('');
    }

    function filteredItems() {
      const q = $('q').value.trim().toLowerCase();
      const cat = $('category').value;
      const curation = $('curationFilter').value;
      return state.items.filter(item => {
        const blob = [item.title, item.summary, item.source_name, item.category, item.editor_note, (item.tags || []).join(',')].join(' ').toLowerCase();
        return (!cat || item.category === cat)
          && (!curation || (item.curation_status || 'candidate') === curation)
          && (!q || blob.includes(q));
      });
    }

    function renderList() {
      const items = filteredItems();
      const accepted = state.items.filter(i => (i.curation_status || 'candidate') === 'accepted').length;
      const candidate = state.items.filter(i => (i.curation_status || 'candidate') === 'candidate').length;
      const rejected = state.items.filter(i => (i.curation_status || 'candidate') === 'rejected').length;
      $('total').textContent = `${items.length} 条`;
      $('checked').textContent = `${state.selected.size} 已选`;
      $('saved').textContent = `采用 ${accepted} / 备选 ${candidate} / 舍弃 ${rejected}`;
      $('list').innerHTML = items.map(item => `
        <div class="row ${state.current && state.current.id === item.id ? 'active' : ''}" data-id="${item.id}">
          <input type="checkbox" data-pick="${item.id}" ${state.selected.has(item.id) ? 'checked' : ''}>
          <div>
            <div class="row-title">${escapeHtml(item.title)}</div>
            <div class="row-summary">${escapeHtml(item.summary || '暂无摘要')}</div>
            <div class="meta">
              <span>${escapeHtml(item.source_name)}</span>
              <span>${escapeHtml(item.category || '综合')}</span>
              <span class="tag ${escapeHtml(item.curation_status || 'candidate')}">${escapeHtml(statusLabel(item.curation_status))}</span>
              ${(item.tags || []).slice(0, 4).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}
            </div>
          </div>
        </div>
      `).join('');
    }

    function openItem(id) {
      const item = state.items.find(i => i.id === id);
      if (!item) return;
      state.current = item;
      $('empty').hidden = true;
      $('form').hidden = false;
      $('title').value = item.title || '';
      $('summary').value = item.summary || '';
      $('editCategory').value = item.category || '';
      $('tags').value = (item.tags || []).join(', ');
      $('curationStatus').value = item.curation_status || 'candidate';
      $('editorNote').value = item.editor_note || '';
      $('url').textContent = item.url;
      $('url').href = item.url;
      $('status').textContent = '';
      renderPreview();
      renderList();
    }

    function renderPreview() {
      const item = state.current;
      if (!item) return;
      $('preview').innerHTML = `
        <strong>${escapeHtml($('title').value)}</strong><br>
        摘要：${escapeHtml($('summary').value)}<br>
        来源：${escapeHtml(item.source_name)} | 状态：${escapeHtml(statusLabel($('curationStatus').value))} | 标签：${escapeHtml($('tags').value)}
      `;
    }

    async function saveCurrent(event) {
      event.preventDefault();
      const item = state.current;
      if (!item) return;
      const payload = {
        title: $('title').value.trim(),
        summary: $('summary').value.trim(),
        category: $('editCategory').value.trim() || '综合',
        tags: $('tags').value.split(',').map(t => t.trim()).filter(Boolean),
        curation_status: $('curationStatus').value,
        editor_note: $('editorNote').value.trim()
      };
      const res = await fetch(apiUrl(`/api/items/${item.id}`), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      if (!res.ok) return showStatus('保存失败', true);
      Object.assign(item, payload);
      if (payload.curation_status === 'rejected') {
        state.selected.delete(item.id);
      } else {
        state.selected.add(item.id);
      }
      showStatus('已保存');
      renderCategories();
      renderList();
      renderPreview();
    }

    async function exportSelected() {
      const ids = [...state.selected];
      if (!ids.length) return showStatus('请至少选择一条资讯', true);
      $('export').disabled = true;
      const res = await fetch(apiUrl('/api/export'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ids })
      });
      $('export').disabled = false;
      const data = await res.json();
      if (!res.ok) return showStatus(data.error || '导出失败', true);
      showStatus(`已导出：${data.path}`);
      $('saved').textContent = `最新导出 ${ids.length} 条`;
      await loadReports();
      await loadQuality();
    }

    async function runNow() {
      $('runNow').disabled = true;
      const days = Number($('runDays').value || 1);
      const translate = $('translateRun') ? $('translateRun').checked : true;
      const rewrite_summary = $('rewriteRun') ? $('rewriteRun').checked : true;
      const res = await fetch(apiUrl('/api/run'), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ days, translate, rewrite_summary })
      });
      if (!res.ok) {
        $('runNow').disabled = false;
        const data = await res.json();
        showStatus(data.error || '启动采集失败', true);
        return;
      }
      showStatus('采集任务已启动');
      const timer = setInterval(async () => {
        await loadSummary();
        const stateRes = await fetch(apiUrl('/api/run-state'));
        const runState = await stateRes.json();
        if (!runState.running) {
          clearInterval(timer);
          $('runNow').disabled = false;
          await loadItems();
          await loadReports();
          await loadQuality();
          showStatus(runState.error ? '采集失败，请查看运行状态' : '采集完成，列表已刷新', Boolean(runState.error));
        }
      }, 2500);
      await loadSummary();
    }

    function showStatus(text, error = false) {
      $('status').textContent = text;
      $('status').className = error ? 'status error' : 'status';
    }

    function statusLabel(status) {
      return {
        accepted: '采用',
        candidate: '备选',
        rejected: '舍弃'
      }[status || 'candidate'] || '备选';
    }

    function apiUrl(path) {
      const token = new URLSearchParams(window.location.search).get('token');
      if (!token) return path;
      const sep = path.includes('?') ? '&' : '?';
      return `${path}${sep}token=${encodeURIComponent(token)}`;
    }

    function escapeHtml(value) {
      return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
      }[ch]));
    }

    function mountRunOptions() {
      if ($('translateRun')) return;
      const runDays = $('runDays');
      const toolbar = runDays ? runDays.parentElement : null;
      if (!toolbar) return;
      const translateLabel = document.createElement('label');
      translateLabel.className = 'inline';
      translateLabel.title = '需要在 Render 环境变量中配置 OPENAI_API_KEY';
      translateLabel.innerHTML = '<input id="translateRun" type="checkbox" checked> 中文翻译';
      const rewriteLabel = document.createElement('label');
      rewriteLabel.className = 'inline';
      rewriteLabel.title = '将摘要改写成公众号日报风格';
      rewriteLabel.innerHTML = '<input id="rewriteRun" type="checkbox" checked> 摘要改写';
      runDays.insertAdjacentElement('afterend', rewriteLabel);
      runDays.insertAdjacentElement('afterend', translateLabel);
    }

    mountRunOptions();

    const pinnedCategories = [
      '外媒涉华开源观察',
      '涉外社媒观察',
      '海外社区舆情',
      '国际 KOL 观点',
      '中国开源项目海外传播',
      '海外大会/CFP 动态'
    ];

    renderCategories = function() {
      const cats = [...new Set([
        ...pinnedCategories,
        ...state.items.map(i => i.category || '综合')
      ])].sort((a, b) => pinnedCategories.includes(a) && !pinnedCategories.includes(b) ? -1 : (!pinnedCategories.includes(a) && pinnedCategories.includes(b) ? 1 : a.localeCompare(b, 'zh-Hans-CN')));
      $('category').innerHTML = '<option value="">全部分类</option>' + cats.map(c => `<option>${escapeHtml(c)}</option>`).join('');
    };

    function formatDuration(seconds) {
      const value = Number(seconds || 0);
      if (!value) return '暂无';
      if (value < 60) return `${Math.round(value)} 秒`;
      const minutes = Math.floor(value / 60);
      const rest = Math.round(value % 60);
      return rest ? `${minutes} 分 ${rest} 秒` : `${minutes} 分`;
    }

    loadSummary = async function() {
      const [summaryRes, stateRes, scheduleRes, qualityRes] = await Promise.all([
        fetch(apiUrl('/api/summary')),
        fetch(apiUrl('/api/run-state')),
        fetch(apiUrl('/api/scheduler')),
        fetch(apiUrl('/api/quality?days=7'))
      ]);
      const summary = await summaryRes.json();
      const runState = await stateRes.json();
      const scheduler = await scheduleRes.json();
      state.quality = await qualityRes.json();
      renderRunPanel(summary, runState, state.quality);
      renderSchedulePanel(scheduler);
    };

    loadQuality = async function() {
      const res = await fetch(apiUrl('/api/quality?days=7'));
      const quality = await res.json();
      state.quality = quality;
      const failed = (quality.failed_sources || []).slice(0, 3).map(s => `${s.name}(${s.failures})`).join('，') || '无';
      $('quality').innerHTML = `
        <span>运行：${escapeHtml(quality.runs ?? 0)}</span>
        <span>成功：${escapeHtml(Math.round((quality.success_rate ?? 0) * 100))}%</span>
        <span>均值：${escapeHtml(quality.average_items ?? 0)} 条</span>
        <span>均时：${escapeHtml(formatDuration(quality.average_duration_seconds))}</span>
        <span>告警：${escapeHtml(quality.total_warnings ?? 0)}</span>
        <span style="grid-column: 1 / -1">失败源：${escapeHtml(failed)}</span>
      `;
    };

    renderRunPanel = function(summary, runState, quality = state.quality || {}) {
      const progress = runState.progress || {};
      const running = runState.running ? '运行中' : (runState.error ? '失败' : '空闲');
      const last = summary.generated_at || '暂无';
      const count = summary.report_items ?? 0;
      const warnings = (summary.warnings || []).length ? summary.warnings.join('；') : '无';
      const failed = Object.values(summary.sources || {}).filter(s => !s.ok).map(s => s.name);
      const percent = Math.max(0, Math.min(100, Number(progress.percent || 0)));
      const latestDuration = progress.duration_seconds || summary.duration_seconds || 0;
      const currentSource = progress.source ? `当前源：${progress.source}` : progress.message || '';
      $('runPanel').innerHTML = `
        <div class="metric-grid">
          <div class="metric"><b>${escapeHtml(running)}</b><span>运行状态</span></div>
          <div class="metric"><b>${escapeHtml(count)}</b><span>最近条目</span></div>
          <div class="metric"><b>${escapeHtml(failed.length)}</b><span>失败源</span></div>
        </div>
        <div class="progress-wrap">
          <div class="progress-track"><div class="progress-fill" style="width:${percent}%"></div></div>
          <div class="progress-meta">
            <span>${escapeHtml(progress.message || '等待采集')} ${runState.running ? `${percent}%` : ''}</span>
            <span>${escapeHtml(currentSource)}</span>
          </div>
        </div>
        <div><strong>最近生成：</strong>${escapeHtml(last)}</div>
        <div><strong>耗时：</strong>${escapeHtml(formatDuration(latestDuration))} | <strong>7 天平均：</strong>${escapeHtml(formatDuration(quality.average_duration_seconds))}</div>
        <div><strong>告警：</strong>${escapeHtml(warnings)}${runState.error ? `；${escapeHtml(runState.error)}` : ''}</div>
      `;
    };

    function shouldShowChinese() {
      return !$('translateRun') || $('translateRun').checked;
    }

    function displayTitle(item) {
      return shouldShowChinese() ? (item.title || item.raw_title || '') : (item.raw_title || item.title || '');
    }

    function displaySummary(item) {
      return shouldShowChinese() ? (item.summary || item.raw_summary || '') : (item.raw_summary || item.summary || '');
    }

    function hasChineseText(value) {
      return /[\u4e00-\u9fff]/.test(String(value || ''));
    }

    function needsChineseTranslation(item) {
      return item && (!hasChineseText(item.title) || !hasChineseText(item.summary || ''));
    }

    async function translateCurrentIfNeeded() {
      const item = state.current;
      if (!item || !shouldShowChinese() || !needsChineseTranslation(item)) return;
      state.translating = state.translating || new Set();
      if (state.translating.has(item.id)) return;
      state.translating.add(item.id);
      showStatus('正在翻译当前条目...');
      try {
        const res = await fetch(apiUrl(`/api/items/${item.id}/translate`), {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({})
        });
        const data = await res.json();
        if (!res.ok) {
          showStatus(data.error || '翻译失败，请检查 API Key 和 Render 日志', true);
          return;
        }
        Object.assign(item, data.item);
        showStatus('翻译完成');
        renderList();
        openItem(item.id);
      } finally {
        state.translating.delete(item.id);
      }
    }

    filteredItems = function() {
      const q = $('q').value.trim().toLowerCase();
      const cat = $('category').value;
      const curation = $('curationFilter').value;
      return state.items.filter(item => {
        const blob = [
          item.title, item.summary, item.raw_title, item.raw_summary,
          item.source_name, item.category, item.editor_note, (item.tags || []).join(',')
        ].join(' ').toLowerCase();
        return (!cat || item.category === cat)
          && (!curation || (item.curation_status || 'candidate') === curation)
          && (!q || blob.includes(q));
      });
    };

    renderList = function() {
      const items = filteredItems();
      const accepted = state.items.filter(i => (i.curation_status || 'candidate') === 'accepted').length;
      const candidate = state.items.filter(i => (i.curation_status || 'candidate') === 'candidate').length;
      const rejected = state.items.filter(i => (i.curation_status || 'candidate') === 'rejected').length;
      $('total').textContent = `${items.length} 条`;
      $('checked').textContent = `${state.selected.size} 已选`;
      $('saved').textContent = `采用 ${accepted} / 备选 ${candidate} / 舍弃 ${rejected}`;
      $('list').innerHTML = items.map(item => `
        <div class="row ${state.current && state.current.id === item.id ? 'active' : ''}" data-id="${item.id}">
          <input type="checkbox" data-pick="${item.id}" ${state.selected.has(item.id) ? 'checked' : ''}>
          <div>
            <div class="row-title">${escapeHtml(displayTitle(item))}</div>
            <div class="row-summary">${escapeHtml(displaySummary(item) || '暂无摘要')}</div>
            <div class="meta">
              <span>${escapeHtml(item.source_name)}</span>
              <span>${escapeHtml(item.category || '综合')}</span>
              <span class="tag ${escapeHtml(item.curation_status || 'candidate')}">${escapeHtml(statusLabel(item.curation_status))}</span>
              ${(item.tags || []).slice(0, 4).map(t => `<span class="tag">${escapeHtml(t)}</span>`).join('')}
            </div>
          </div>
        </div>
      `).join('');
    };

    openItem = function(id) {
      const item = state.items.find(i => i.id === id);
      if (!item) return;
      state.current = item;
      $('empty').hidden = true;
      $('form').hidden = false;
      $('title').value = displayTitle(item) || '';
      $('summary').value = displaySummary(item) || '';
      $('editCategory').value = item.category || '';
      $('tags').value = (item.tags || []).join(', ');
      $('curationStatus').value = item.curation_status || 'candidate';
      $('editorNote').value = item.editor_note || '';
      $('url').textContent = item.url;
      $('url').href = item.url;
      $('status').textContent = '';
      renderPreview();
      renderList();
      if (shouldShowChinese() && needsChineseTranslation(item)) {
        setTimeout(() => translateCurrentIfNeeded(), 0);
      }
    };

    renderPreview = function() {
      const item = state.current;
      if (!item) return;
      $('preview').innerHTML = `
        <strong>${escapeHtml($('title').value)}</strong><br>
        摘要：${escapeHtml($('summary').value)}<br>
        来源：${escapeHtml(item.source_name)} | 状态：${escapeHtml(statusLabel($('curationStatus').value))} | 标签：${escapeHtml($('tags').value)}
      `;
    };

    statusLabel = function(status) {
      return {
        accepted: '采用',
        candidate: '备选',
        rejected: '舍弃'
      }[status || 'candidate'] || '备选';
    };

    $('translateRun').addEventListener('change', () => {
      renderList();
      if (state.current) openItem(state.current.id);
      translateCurrentIfNeeded();
    });

    $('list').addEventListener('click', event => {
      const pick = event.target.closest('[data-pick]');
      if (pick) {
        const id = Number(pick.dataset.pick);
        pick.checked ? state.selected.add(id) : state.selected.delete(id);
        renderList();
        return;
      }
      const row = event.target.closest('[data-id]');
      if (row) openItem(Number(row.dataset.id));
    });
    $('q').addEventListener('input', renderList);
    $('category').addEventListener('change', renderList);
    $('curationFilter').addEventListener('change', renderList);
    $('form').addEventListener('submit', saveCurrent);
    ['title', 'summary', 'editCategory', 'tags', 'curationStatus', 'editorNote'].forEach(id => $(id).addEventListener('input', renderPreview));
    $('selectAll').addEventListener('click', () => { filteredItems().forEach(i => state.selected.add(i.id)); renderList(); });
    $('selectNone').addEventListener('click', () => { filteredItems().forEach(i => state.selected.delete(i.id)); renderList(); });
    $('togglePick').addEventListener('click', () => {
      if (!state.current) return;
      state.selected.has(state.current.id) ? state.selected.delete(state.current.id) : state.selected.add(state.current.id);
      renderList();
    });
    $('export').addEventListener('click', exportSelected);
    $('runNow').addEventListener('click', runNow);
    loadItems();
    loadSummary();
    loadReports();
    loadQuality();
    loadVersion();
  </script>
</body>
</html>
"""

LOGIN_HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>开源日报编辑台登录</title>
  <style>
    body {
      margin: 0;
      min-height: 100vh;
      display: grid;
      place-items: center;
      background: #f6f7f9;
      color: #1f2937;
      font-family: "Segoe UI", "Microsoft YaHei", Arial, sans-serif;
      font-size: 14px;
      letter-spacing: 0;
    }
    form {
      width: min(420px, calc(100vw - 32px));
      background: #fff;
      border: 1px solid #d9dee7;
      border-radius: 8px;
      padding: 24px;
      display: grid;
      gap: 14px;
    }
    h1 { margin: 0; font-size: 20px; }
    input, button {
      border: 1px solid #d9dee7;
      border-radius: 6px;
      padding: 10px 12px;
      font: inherit;
    }
    button {
      background: #2563eb;
      color: #fff;
      border-color: #2563eb;
      cursor: pointer;
    }
  </style>
</head>
<body>
  <form id="login">
    <h1>开源日报编辑台</h1>
    <input id="token" type="password" placeholder="输入 ADMIN_TOKEN" autofocus>
    <button type="submit">进入</button>
  </form>
  <script>
    document.getElementById('login').addEventListener('submit', event => {
      event.preventDefault();
      const token = document.getElementById('token').value.trim();
      if (token) window.location.href = '/?token=' + encodeURIComponent(token);
    });
  </script>
</body>
</html>
"""


def serve_admin(
    db_path: Path,
    output_dir: Path,
    host: str = "127.0.0.1",
    port: int = 8765,
    sources_path: Path = Path("configs/sources.yaml"),
    rules_path: Path = Path("configs/keywords.yaml"),
    schedule: bool = False,
    schedule_time: str = "06:00",
    notify: bool = False,
    translate: bool = False,
    translate_provider: str = "openai",
    translation_limit: int = 30,
    rewrite_summary: bool = False,
    min_items: int = 5,
    max_items: int = 120,
) -> None:
    run_options = RunOptions(
        days=1,
        sources=sources_path,
        rules=rules_path,
        db=db_path,
        output=output_dir,
        notify=notify,
        translate=translate,
        translate_provider=translate_provider,
        translation_limit=translation_limit,
        rewrite_summary=rewrite_summary,
        min_items=min_items,
        max_items=max_items,
    )
    scheduler_state = start_daily_scheduler(run_options, schedule_time=schedule_time) if schedule else SchedulerState(
        enabled=False,
        schedule_time=schedule_time,
    )
    handler = build_handler(db_path, output_dir, sources_path, rules_path, scheduler_state, run_options)
    server = ThreadingHTTPServer((host, port), handler)
    print(f"Open Source Daily admin: http://{host}:{port}")
    server.serve_forever()


def build_handler(
    db_path: Path,
    output_dir: Path,
    sources_path: Path,
    rules_path: Path,
    scheduler_state: SchedulerState,
    run_options: RunOptions,
) -> type[BaseHTTPRequestHandler]:
    run_state = {
        "running": False,
        "started_at": None,
        "finished_at": None,
        "error": None,
        "result": None,
        "progress": {
            "phase": "idle",
            "message": "空闲",
            "percent": 0,
            "current": 0,
            "total": 0,
            "source": "",
            "elapsed_seconds": 0,
        },
    }
    state_lock = threading.Lock()

    class AdminHandler(BaseHTTPRequestHandler):
        def handle_one_request(self) -> None:
            super().handle_one_request()

        def is_authorized(self) -> bool:
            token = os.getenv("ADMIN_TOKEN", "").strip()
            if not token:
                return True
            parsed = urlparse(self.path)
            query_token = parse_qs(parsed.query).get("token", [""])[0]
            header_token = self.headers.get("X-Admin-Token", "")
            return token in {query_token, header_token}

        def require_auth(self) -> bool:
            if self.is_authorized():
                return True
            self.send_json({"error": "unauthorized"}, HTTPStatus.UNAUTHORIZED)
            return False

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path == "/healthz":
                self.send_json({"ok": True, "version": __version__})
                return
            if parsed.path == "/api/version":
                self.send_json({"version": __version__, "features": ["raw-source-toggle", "llm-provider-switch"]})
                return
            if parsed.path == "/":
                if not self.is_authorized():
                    self.send_html(LOGIN_HTML, HTTPStatus.UNAUTHORIZED)
                    return
                self.send_html(HTML)
                return
            if not self.require_auth():
                return
            if parsed.path == "/api/items":
                query = parse_qs(parsed.query)
                limit = int(query.get("limit", ["300"])[0])
                store = Store(db_path)
                try:
                    records = store.list_item_records(limit=limit)
                finally:
                    store.close()
                self.send_json(records)
                return
            if parsed.path == "/api/summary":
                self.send_json(load_latest_summary(output_dir))
                return
            if parsed.path == "/api/run-state":
                with state_lock:
                    self.send_json(dict(run_state))
                return
            if parsed.path == "/api/scheduler":
                self.send_json(scheduler_state.snapshot())
                return
            if parsed.path == "/api/reports":
                self.send_json(list_reports(output_dir))
                return
            if parsed.path == "/api/quality":
                query = parse_qs(parsed.query)
                days = max(1, min(30, int(query.get("days", ["7"])[0])))
                self.send_json(build_quality_report(output_dir, days=days))
                return
            if parsed.path.startswith("/reports/"):
                name = parsed.path.rsplit("/", 1)[-1]
                self.send_report(output_dir, name)
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def do_POST(self) -> None:
            if not self.require_auth():
                return
            parsed = urlparse(self.path)
            if parsed.path.startswith("/api/items/") and parsed.path.endswith("/translate"):
                item_id = int(parsed.path.split("/")[-2])
                store = Store(db_path)
                try:
                    record = store.get_item_record(item_id)
                    if not record:
                        self.send_json({"error": "item not found"}, HTTPStatus.NOT_FOUND)
                        return
                    source_title = record.get("raw_title") or record.get("title") or ""
                    source_summary = record.get("raw_summary") or record.get("summary") or ""
                    item = NewsItem(
                        title=source_title,
                        summary=source_summary,
                        raw_title=source_title,
                        raw_summary=source_summary,
                        url=record["url"],
                        source_id=record["source_id"],
                        source_name=record["source_name"],
                        category=record["category"],
                        tags=record["tags"],
                    )
                    provider = os.getenv("TRANSLATION_PROVIDER", run_options.translate_provider)
                    client_config = resolve_provider(provider)
                    if not client_config["api_key"]:
                        self.send_json({"error": f"{client_config['api_key_env']} is required"}, HTTPStatus.BAD_REQUEST)
                        return
                    key = cache_key(item, build_mode(True, True))
                    cached = store.get_translation(key)
                    if cached:
                        title, summary = cached
                    else:
                        title, summary = enrich_with_llm(source_title, source_summary, True, True, client_config)
                        store.save_translation(key, title, summary)
                    store.update_translation_fields(item_id, title, summary, source_title, source_summary)
                    updated = store.get_item_record(item_id)
                finally:
                    store.close()
                self.send_json({"ok": True, "item": updated})
                return
            if parsed.path.startswith("/api/items/"):
                item_id = int(parsed.path.rsplit("/", 1)[-1])
                payload = self.read_json()
                tags = payload.get("tags", [])
                if isinstance(tags, str):
                    tags = [tag.strip() for tag in tags.split(",") if tag.strip()]
                store = Store(db_path)
                try:
                    ok = store.update_item(
                        item_id,
                        str(payload.get("title", "")).strip(),
                        str(payload.get("summary", "")).strip(),
                        str(payload.get("category", "综合")).strip() or "综合",
                        list(tags),
                        str(payload.get("curation_status", "candidate")),
                        str(payload.get("editor_note", "")).strip(),
                    )
                finally:
                    store.close()
                if not ok:
                    self.send_json({"error": "item not found"}, HTTPStatus.NOT_FOUND)
                    return
                self.send_json({"ok": True})
                return
            if parsed.path == "/api/export":
                payload = self.read_json()
                ids = [int(item_id) for item_id in payload.get("ids", [])]
                store = Store(db_path)
                try:
                    if not ids:
                        ids = [
                            int(record["id"])
                            for record in store.list_item_records(limit=1000)
                            if record.get("curation_status") == "accepted"
                        ]
                    items = store.items_by_ids(ids)
                finally:
                    store.close()
                if not items:
                    self.send_json({"error": "no selected items"}, HTTPStatus.BAD_REQUEST)
                    return
                path = write_report(
                    items,
                    output_dir,
                    datetime.now().astimezone(),
                    {"process": {"accepted": len(items)}, "enrichment": {}, "warnings": []},
                )
                self.send_json({"ok": True, "path": str(path), "count": len(items)})
                return
            if parsed.path == "/api/run":
                payload = self.read_json()
                days = max(1, min(14, int(payload.get("days", 1))))
                translate = bool(payload.get("translate", run_options.translate))
                rewrite_summary = bool(payload.get("rewrite_summary", run_options.rewrite_summary))
                with state_lock:
                    if run_state["running"]:
                        self.send_json({"error": "采集任务正在运行"}, HTTPStatus.CONFLICT)
                        return
                    run_state.update({
                        "running": True,
                        "started_at": datetime.now().astimezone().isoformat(),
                        "finished_at": None,
                        "error": None,
                        "result": None,
                        "progress": {
                            "phase": "collecting",
                            "message": "准备采集",
                            "percent": 1,
                            "current": 0,
                            "total": 0,
                            "source": "",
                            "elapsed_seconds": 0,
                        },
                    })
                thread = threading.Thread(
                    target=self.run_in_background,
                    args=(days, translate, rewrite_summary),
                    daemon=True,
                )
                thread.start()
                self.send_json({"ok": True, "days": days, "translate": translate, "rewrite_summary": rewrite_summary})
                return
            self.send_error(HTTPStatus.NOT_FOUND)

        def update_run_progress(self, payload: dict) -> None:
            phase = str(payload.get("phase") or "collecting")
            current = int(payload.get("current") or 0)
            total = max(0, int(payload.get("total") or 0))
            source = str(payload.get("source") or "")
            phase_ranges = {
                "collecting": (2, 72),
                "processing": (73, 82),
                "enriching": (83, 94),
                "storing": (95, 98),
                "done": (100, 100),
            }
            start, end = phase_ranges.get(phase, (2, 98))
            if total > 0 and phase == "collecting":
                percent = start + round((end - start) * min(current, total) / total)
            else:
                percent = end
            labels = {
                "collecting": "采集中",
                "processing": "过滤去重中",
                "enriching": "翻译/改写中",
                "storing": "写入数据库中",
                "done": "已完成",
            }
            with state_lock:
                started_at = run_state.get("started_at")
                elapsed = 0.0
                if started_at:
                    try:
                        elapsed = (datetime.now().astimezone() - datetime.fromisoformat(str(started_at))).total_seconds()
                    except ValueError:
                        elapsed = 0.0
                run_state["progress"] = {
                    "phase": phase,
                    "message": labels.get(phase, phase),
                    "percent": max(0, min(100, percent)),
                    "current": current,
                    "total": total,
                    "source": source,
                    "elapsed_seconds": round(elapsed, 1),
                    "duration_seconds": payload.get("duration_seconds"),
                }

        def run_in_background(self, days: int, translate: bool, rewrite_summary: bool) -> None:
            try:
                result = run_pipeline(
                    RunOptions(
                        days=days,
                        sources=sources_path,
                        rules=rules_path,
                        db=db_path,
                        output=output_dir,
                        notify=run_options.notify,
                        translate=translate,
                        translate_provider=run_options.translate_provider,
                        translation_limit=run_options.translation_limit,
                        rewrite_summary=rewrite_summary,
                        min_items=run_options.min_items,
                        max_items=run_options.max_items,
                    ),
                    progress_callback=self.update_run_progress,
                )
                with state_lock:
                    run_state.update({
                        "running": False,
                        "finished_at": datetime.now().astimezone().isoformat(),
                        "error": None,
                        "result": result,
                        "progress": {
                            "phase": "done",
                            "message": "已完成",
                            "percent": 100,
                            "current": 100,
                            "total": 100,
                            "source": "",
                            "elapsed_seconds": result.get("stats", {}).get("duration_seconds", 0),
                            "duration_seconds": result.get("stats", {}).get("duration_seconds", 0),
                        },
                    })
            except Exception as exc:
                with state_lock:
                    run_state.update({
                        "running": False,
                        "finished_at": datetime.now().astimezone().isoformat(),
                        "error": str(exc),
                        "result": None,
                        "progress": {
                            "phase": "error",
                            "message": "采集失败",
                            "percent": 100,
                            "current": 0,
                            "total": 0,
                            "source": "",
                            "elapsed_seconds": run_state.get("progress", {}).get("elapsed_seconds", 0),
                        },
                    })

        def read_json(self) -> dict:
            length = int(self.headers.get("Content-Length", "0"))
            raw = self.rfile.read(length).decode("utf-8") if length else "{}"
            return json.loads(raw or "{}")

        def send_html(self, html: str, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = html.encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def send_report(self, output_dir: Path, name: str) -> None:
            path = safe_report_path(output_dir, name)
            if path is None or not path.exists():
                self.send_error(HTTPStatus.NOT_FOUND)
                return
            data = path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/markdown; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def log_message(self, format: str, *args: object) -> None:
            return

    return AdminHandler


def load_latest_summary(output_dir: Path, fallback_daily: bool = True) -> dict:
    candidates = sorted(output_dir.glob("run-summary-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if fallback_daily and not candidates and output_dir != Path("output/daily"):
        candidates = sorted(Path("output/daily").glob("run-summary-*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates:
        return {
            "generated_at": None,
            "report_items": 0,
            "process": {},
            "enrichment": {},
            "sources": {},
            "warnings": [],
        }
    try:
        return json.loads(candidates[0].read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "generated_at": None,
            "report_items": 0,
            "process": {},
            "enrichment": {},
            "sources": {},
            "warnings": [f"读取运行摘要失败：{exc}"],
        }


def list_reports(output_dir: Path) -> list[dict]:
    candidates = sorted(output_dir.glob("open-source-daily-*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    if not candidates and output_dir != Path("output/daily"):
        candidates = sorted(Path("output/daily").glob("open-source-daily-*.md"), key=lambda path: path.stat().st_mtime, reverse=True)
    return [
        {
            "name": path.name,
            "size": path.stat().st_size,
            "modified_at": datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(),
        }
        for path in candidates[:10]
    ]


def safe_report_path(output_dir: Path, name: str) -> Path | None:
    if "/" in name or "\\" in name or not name.endswith(".md"):
        return None
    primary = output_dir / name
    if primary.exists():
        return primary
    fallback = Path("output/daily") / name
    if fallback.exists():
        return fallback
    return primary
